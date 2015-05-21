angular.module('windmobile.controllers', ['windmobile.services'])

    .controller('ListController', ['$state', '$http', 'utils', function ($state, $http, utils) {
        var self = this;

        function geoSearch(position) {
            var params = {};
            params.lat = position.coords.latitude;
            params.lon = position.coords.longitude;
            $http({method: 'GET', url: '/api/2/stations/', params: params}).
                success(function (data) {
                    self.stations = data;
                    for (var i = 0; i < self.stations.length; i++) {
                        self.getHistoric(self.stations[i]);
                    }
                });
        }
        function search() {
            var params = {};
            params.search = self.query;
            $http({method: 'GET', url: '/api/2/stations/', params: params}).
                success(function (data) {
                    self.stations = data;
                    for (var i = 0; i < self.stations.length; i++) {
                        self.getHistoric(self.stations[i]);
                    }
                });
        }
        function getGeoLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(geoSearch, search, {
                    enableHighAccuracy: true,
                    timeout: 3000,
                    maximumAge: 300000
                });
            }
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
        this.list = function () {
            if (this.query) {
                search();
            } else {
                getGeoLocation();
            }
        };
        this.list();
    }])

    .controller('MapController', ['$scope', '$state', '$http', '$compile', '$templateCache', 'utils',
        function ($scope, $state, $http, $compile, $templateCache, utils) {
            var self = this;
            var markersArray = [];
            var inboBoxContent = $compile($templateCache.get('_infobox.html'))($scope);

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

            function clearOverlays() {
                if (self.infoBox) {
                    self.infoBox.close();
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
                        scale: 0.15,
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
                            if (self.infoBox) {
                                self.infoBox.close();
                            }
                            self.selectedStation = marker.station;
                            self.getHistoric();
                            self.infoBox = new InfoBox({
                                content: inboBoxContent[0],
                                closeBoxURL: ''
                            });
                            self.infoBox.open(self.map, marker);
                        })
                    })(marker);

                    google.maps.event.addListener(self.map, 'click', function () {
                        if (self.infoBox) {
                            self.infoBox.close();
                        }
                    });
                }
            }

            function geoSearch(position) {
                var currentPosition = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
                self.map.setCenter(currentPosition);
                self.map.setZoom(8);

                var params = {};
                params.lat = position.coords.latitude;
                params.lon = position.coords.longitude;
                params.limit = 1000;

                $http({method: 'GET', url: '/api/2/stations/', params: params}).success(displayMarkers);
            }

            function search() {
                var params = {};
                params.search = self.query;
                params.limit = 1000;
                $http({method: 'GET', url: '/api/2/stations/', params: params}).success(displayMarkers);
            }

            function getGeoLocation() {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(geoSearch, search, {
                        enableHighAccuracy: true,
                        timeout: 3000,
                        maximumAge: 300000
                    });
                }
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
                if (this.infoBox) {
                    this.infoBox.close();
                }
                $state.go('map.detail', {stationId: this.selectedStation._id});
            };
            this.list = function () {
                if (this.query) {
                    search();
                } else {
                    getGeoLocation();
                }
            };
            this.list();
        }])

    .controller('DetailController', ['$state', '$stateParams', '$http',
        function ($state, $stateParams, $http) {
            var self = this;

            $('#detailModal').modal();
            $('#detailModal').on('hidden.bs.modal', function (e) {
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
                        historic['w-avg'] = {};
                        historic['w-avg'].min = Math.min.apply(null, data.map(windAvg));
                        historic['w-avg'].mean = data.map(windAvg).reduce(function (previousValue, currentValue) {
                                return previousValue + currentValue;
                            }, 0) / data.length;
                        historic['w-avg'].max = Math.max.apply(null, data.map(windAvg));
                        self.stationHistoric = historic;
                    })
            };
            this.getStation();
            this.getStationHistoric();
        }]);