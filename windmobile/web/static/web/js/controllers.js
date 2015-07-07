angular.module('windmobile.controllers', ['windmobile.services'])

    .controller('ListController', ['$scope', '$state', '$http', '$interval', 'utils', function ($scope, $state, $http, $interval, utils) {
        var self = this;

        function search(position) {
            var params = {};
            if (position) {
                params['near-lat'] = position.coords.latitude;
                params['near-lon'] = position.coords.longitude;
            }
            params.search = self.search;
            params.limit = 12;

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

        $scope.onRefreshInterval = function() {
            self.doSearch();
        };

        $scope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
            if (toState.name === 'list') {
                $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
            } else if (fromState.name === 'list') {
                $interval.cancel($scope.refreshInterval);
            }
            // Force modal to close on browser back
            $('#detailModal').modal('hide');
        });

        $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
        this.doSearch();
    }])

    .controller('MapController', ['$scope', '$state', '$http', '$compile', '$templateCache', '$interval', 'utils',
        function ($scope, $state, $http, $compile, $templateCache, $interval, utils) {
            var infoBox;
            var inboBoxContent = $compile($templateCache.get('_infobox.html'))($scope);

            var self = this;

            var markersArray = [];
            function getMarker(id) {
                for (var i = 0; i < markersArray.length; i++) {
                    var marker = markersArray[i];
                    if (marker.station._id === id) {
                        return marker;
                    }
                }
                return null;
            }

            function hasStation(id, stations) {
                for (var i = 0; i < stations.length; i++) {
                    if (stations[i]._id === id) {
                        return true;
                    }
                }
                return false;
            }

            function displayMarkers(stations) {
                for (var i = 0; i < markersArray.length; i++) {
                    var marker = markersArray[i];
                    if (!hasStation(marker.station._id, stations)) {
                        google.maps.event.clearInstanceListeners(marker);
                        marker.setMap(null);
                        markersArray.splice(i, 1);
                        i--;
                    }
                }

                for (i = 0; i < stations.length; i++) {
                    var station = stations[i];
                    var marker = getMarker(station._id);

                    var color;
                    if (utils.getStationStatus(station) == 0) {
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

                    if (!marker) {
                        marker = new google.maps.Marker({
                            title: station["short"],
                            position: new google.maps.LatLng(station.loc.coordinates[1], station.loc.coordinates[0]),
                            icon: icon,
                            map: self.map
                        });
                        marker.station = station;
                        markersArray.push(marker);

                        google.maps.event.addListener(marker, 'click', function () {
                            // 'click' is also called twice on 'dbckick' event
                            if (!this.timeout) {
                                marker = this;
                                this.timeout = setTimeout(function () {
                                    marker.timeout = null;
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
                                }, 300);
                            }
                        });
                        google.maps.event.addListener(marker, 'dblclick', function (event) {
                            clearTimeout(this.timeout);
                            this.timeout = null;
                            throw "propagates dblclick event";
                        });
                    } else {
                        marker.setIcon(icon);
                    }
                }
            }
            function search(bounds) {
                var params = {};
                if (bounds) {
                    params['within-pt1-lat'] = bounds.getNorthEast().lat();
                    params['within-pt1-lon'] = bounds.getNorthEast().lng();
                    params['within-pt2-lat'] = bounds.getSouthWest().lat();
                    params['within-pt2-lon'] = bounds.getSouthWest().lng();
                }
                params.search = self.search;
                params.limit = 100;

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
                search(this.map.getBounds());
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
            google.maps.event.addListener(self.map, 'bounds_changed', (function () {
                var timer;
                return function () {
                    if (infoBox) {
                        infoBox.close();
                    }
                    
                    clearTimeout(timer);
                    timer = setTimeout(function () {
                        self.doSearch();
                    }, 500);
                }
            }()));

            $scope.onRefreshInterval = function() {
                self.doSearch();
            };

            $scope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
                if (toState.name === 'map') {
                    $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
                } else if (fromState.name === 'map') {
                    $interval.cancel($scope.refreshInterval);
                }
                // Force modal to close on browser back
                $('#detailModal').modal('hide');
            });

            $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
            this.centerMap();
        }])

    .controller('DetailController', ['$scope', '$state', '$stateParams', '$http', '$interval', 'utils',
        function ($scope, $state, $stateParams, $http, $interval, utils) {
            var self = this;

            $('#detailModal').modal().on('hidden.bs.modal', function (e) {
                $state.go('^');
            });

            $('a[data-target="#tab2"]').on('shown.bs.tab', function (event) {
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + $stateParams.stationId + '/historic?duration=432000'
                }).success(function (data) {
                    self.stationWindChart = data;
                });
            });
            $('a[data-target="#tab3"]').on('shown.bs.tab', function (event) {
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + $stateParams.stationId + '/historic?duration=432000'
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
            this.doDetail = function () {
                this.getStation();
                this.getStationHistoric();
            };

            $scope.onRefreshInterval = function() {
                self.doDetail();
            };

            $scope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
                if (toState.name.indexOf('detail') > -1) {
                    $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
                } else if (fromState.name.indexOf('detail') > -1) {
                    $interval.cancel($scope.refreshInterval);
                }
            });

            $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
            this.doDetail();
        }]);