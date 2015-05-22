angular.module('windmobile.controllers', ['windmobile.services'])

    .controller('ListController', ['$rootScope', '$state', '$http', 'utils', function ($rootScope, $state, $http, utils) {
        var self = this;

        function search(position) {
            var params = {};
            if (position) {
                params.lat = position.coords.latitude;
                params.lon = position.coords.longitude;
            }
            params.search = self.search;
            $http({method: 'GET', url: '/api/2/stations/', params: params}).
                success(function (data) {
                    self.stations = data;
                    for (var i = 0; i < self.stations.length; i++) {
                        self.getHistoric(self.stations[i]);
                    }
                });
        }

        this.getStatusClass = function (station) {
            if (station) {
                var status = utils.getStationStatus(station);
                return utils.getStatusClass(status);
            }
        };
        this.getHistoric = function (station) {
            $http({method: 'GET', url: '/api/2/stations/' + station._id + '/historic?duration=3600'}).
                success(function (data) {
                    var historic = {
                        data: data
                    };
                    station.historic = historic;
                });
        };
        this.selectStation = function (station) {
            $state.go('list.detail', {stationId: station._id});
        };
        this.doSearch = function () {
            if (navigator.geolocation) {
                var locationTimeout = setTimeout(search, 1000);
                navigator.geolocation.getCurrentPosition(function(position) {
                    clearTimeout(locationTimeout);
                    search(position);
                }, function(error) {
                    clearTimeout(locationTimeout);
                    search();
                }, {
                    enableHighAccuracy: true,
                    maximumAge: 300000
                });
            } else {
                search();
            }
        };
        this.clearSearch = function () {
            this.search = null;
            this.doSearch();
        };

        // Force modal to close on browser back
        $rootScope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
            $('#detailModal').modal('hide');
        });

        this.doSearch();
    }])

    .controller('MapController', ['$rootScope', '$scope', '$state', '$http', '$compile', '$templateCache', 'utils',
        function ($rootScope, $scope, $state, $http, $compile, $templateCache, utils) {
            var markersArray = [];
            var infoBox;
            var inboBoxContent = $compile($templateCache.get('_infobox.html'))($scope);

            var self = this;

            function clearOverlays() {
                if (infoBox) {
                    infoBox.close();
                }
                for (var i = 0; i < markersArray.length; i++) {
                    markersArray[i].setMap(null);
                }
                markersArray.length = 0;
            }
            function displayMarkers(stations) {
                clearOverlays();

                for (var i = 0; i < stations.length; i++) {
                    var station = stations[i];
                    var status = utils.getStationStatus(station);

                    var color;
                    if (status == 0) {
                        color = '#808080';
                    } else {
                        color = utils.getColorInRange(station.last['w-max'], 50);
                    }

                    var icon = {
                        path: 'M21,149.2v86.3L-19,213l50,77l50-77l-40,22.5v-86.3c28.4-4.8,50-29.4,50-59.2S69.4,35.6,41,30.8V-83H21V30.8C-7.4,35.6-29,60.3-29,90S-7.4,144.4,21,149.2z M31,50c22.1,0,40,17.9,40,40s-17.9,40-40,40S-9,112.1-9,90S8.9,50,31,50z',
                        anchor: new google.maps.Point(31, 90),
                        scale: 0.12,
                        fillOpacity: 1,
                        fillColor: color,
                        strokeColor: color,
                        strokeWeight: 2,
                        rotation: (station.last ? station.last['w-dir'] : 0)
                    };

                    var marker = new google.maps.Marker({
                        title: station["short"],
                        position: new google.maps.LatLng(station.loc.coordinates[1], station.loc.coordinates[0]),
                        icon: icon,
                        map: self.map
                    });
                    marker.station = station;
                    markersArray.push(marker);

                    (function (marker) {
                        google.maps.event.addListener(marker, 'click', function () {
                            if (infoBox) {
                                infoBox.close();
                            }
                            self.selectedStation = marker.station;
                            self.getHistoric();
                            infoBox = new InfoBox({
                                content: inboBoxContent[0],
                                closeBoxURL: ''
                            });
                            infoBox.open(self.map, marker);
                        })
                    })(marker);
                }
            }
            function search(position) {
                var params = {};
                if (position) {
                    params.lat = position.lat();
                    params.lon = position.lng();
                }
                params.search = self.search;
                params.limit = 500;

                $http({method: 'GET', url: '/api/2/stations/', params: params}).success(displayMarkers);
            }

            this.getStatusClass = function (station) {
                if (station) {
                    var status = utils.getStationStatus(station);
                    return utils.getStatusClass(status);
                }
            };
            this.getHistoric = function () {
                $http({method: 'GET', url: '/api/2/stations/' + this.selectedStation._id + '/historic?duration=3600'})
                    .success(function (data) {
                        var historic = {};
                        historic.data = data;
                        var windAvg = function (value) {
                            return value['w-avg'];
                        };
                        historic['w-avg'] = {};
                        historic['w-avg'].min = Math.min.apply(null, data.map(windAvg));
                        historic['w-avg'].mean = data.map(windAvg).reduce(function (previousValue, currentValue) {
                                return previousValue + currentValue;
                            }, 0) / data.length;
                        historic['w-avg'].max = Math.max.apply(null, data.map(windAvg));
                        self.selectedStation.historic = historic;
                    })
            };
            this.selectStation = function () {
                if (infoBox) {
                    infoBox.close();
                }
                $state.go('map.detail', {stationId: this.selectedStation._id});
            };
            this.doSearch = function () {
                search(this.map.getCenter());
            };
            this.clearSearch = function () {
                this.search = null;
                this.doSearch();
            };
            this.centerMap = function () {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(function(position) {
                        var currentPosition = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
                        self.map.panTo(currentPosition);
                        self.map.setZoom(8);
                        //search(currentPosition);
                    }, null, {
                        enableHighAccuracy: true,
                        maximumAge: 300000
                    });
                }
            };

            // Initialize Google Maps
            var mapOptions = {
                // France and Switzerland
                center: new google.maps.LatLng(46.76, 4.08),
                zoom: 6,
                panControl: false,
                mapTypeControlOptions: {
                    mapTypeIds: [google.maps.MapTypeId.TERRAIN, google.maps.MapTypeId.ROADMAP,
                        google.maps.MapTypeId.SATELLITE]
                },
                mapTypeId: google.maps.MapTypeId.TERRAIN
            };
            this.map = new google.maps.Map(document.getElementById('map-canvas'), mapOptions);
            google.maps.event.addListener(self.map, 'click', function () {
                if (infoBox) {
                    infoBox.close();
                }
            });

            // Force modal to close on browser back
            $rootScope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
                $('#detailModal').modal('hide');
            });

            this.doSearch();
            this.centerMap();
        }])

    .controller('DetailController', ['$state', '$stateParams', '$http',
        function ($state, $stateParams, $http) {
            var self = this;

            $('#detailModal').modal().on('hidden.bs.modal', function (e) {
                $state.go('^');
            });

            $('a[data-target="#tab2"]').on('shown.bs.tab', function (event) {
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + $stateParams.stationId + '/historic?duration=172800'
                }).success(function (data) {
                    self.stationWindChart = data;
                });
            });
            $('a[data-target="#tab3"]').on('shown.bs.tab', function (event) {
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + $stateParams.stationId + '/historic?duration=172800'
                }).success(function (data) {
                    self.stationAirChart = data;
                });
            });

            this.getStation = function () {
                $http({method: 'GET', url: '/api/2/stations/' + $stateParams.stationId}).
                    success(function (data) {
                        self.station = data;
                    });
            };
            this.getStationHistoric = function () {
                $http({method: 'GET', url: '/api/2/stations/' + $stateParams.stationId + '/historic?duration=3600'})
                    .success(function (data) {
                        var historic = {
                            data: data
                        };
                        var windAvg = function (value) {
                            return value['w-avg'];
                        };
                        var windMax = function (value) {
                            return value['w-max'];
                        };
                        historic['lastHour'] = {};
                        historic['lastHour'].min = Math.min.apply(null, data.map(windAvg));
                        historic['lastHour'].mean = data.map(windAvg).reduce(function (previousValue, currentValue) {
                                return previousValue + currentValue;
                            }, 0) / data.length;
                        historic['lastHour'].max = Math.max.apply(null, data.map(windMax));
                        self.stationHistoric = historic;
                    })
            };
            this.getStation();
            this.getStationHistoric();
        }]);