var angular = require('angular');
var moment = require('moment');
var InfoBox = require('google-maps-infobox');

angular.module('windmobile.controllers', ['windmobile.services'])

    .controller('ListController', ['$scope', '$state', '$http', '$interval', 'utils', function ($scope, $state, $http, $interval, utils) {
        var self = this;

        function search(position) {
            var params = {
                proj: ['short', 'loc', 'status', 'prov', 'alt', 'last._id', 'last.w-dir', 'last.w-avg', 'last.w-max']
            };
            if (position) {
                params['near-lat'] = position.coords.latitude;
                params['near-lon'] = position.coords.longitude;
            }
            params.search = self.search;
            params.limit = 12;

            $http({
                method: 'GET',
                url: '/api/2/stations/',
                params: params
            }).success(function (data) {
                self.stations = data;
                for (var i = 0; i < self.stations.length; i++) {
                    var station = self.stations[i];
                    station.fromNow = moment.unix(station.last._id).fromNow();
                    var status = utils.getStationStatus(station);
                    station.fromNowClass = utils.getStatusClass(status);
                    self.getHistoric(station);
                }
            });
        }
        this.getHistoric = function (station) {
            var params = {
                duration: 3600,
                proj: ['w-dir', 'w-avg']
            };
            $http({
                method: 'GET',
                url: '/api/2/stations/' + station._id + '/historic',
                params: params
            }).success(function (data) {
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

        $scope.onFromNowInterval = function() {
            for (var i = 0; i < self.stations.length; i++) {
                var station = self.stations[i];
                station.fromNow = moment.unix(station.last._id).fromNow();
                var status = utils.getStationStatus(station);
                station.fromNowClass = utils.getStatusClass(status);
            }
        };
        $scope.onRefreshInterval = function() {
            self.doSearch();
        };

        $scope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
            if (toState.name === 'list') {
                $scope.fromNowInterval = $interval($scope.onFromNowInterval, utils.fromNowInterval);
                $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
            } else if (fromState.name === 'list') {
                $interval.cancel($scope.fromNowInterval);
                $interval.cancel($scope.refreshInterval);
            }
            // Force modal to close on browser back
            $('#detailModal').modal('hide');
        });

        $scope.fromNowInterval = $interval($scope.onFromNowInterval, utils.fromNowInterval);
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

                    if (self.selectedStation && self.selectedStation._id === station._id) {
                        self.selectedStation = station;
                        self.selectedStation.fromNow = moment.unix(self.selectedStation.last._id).fromNow();
                        var status = utils.getStationStatus(self.selectedStation);
                        self.selectedStation.fromNowClass = utils.getStatusClass(status);
                        self.getHistoric();
                    }

                    var color;
                    if (utils.getStationStatus(station) == 0) {
                        color = '#808080';
                    } else {
                        color = utils.getColorInRange(station.last['w-max'], 50);
                    }
                    var icon = {
                        path: (station.peak ?
                            "M10,60v-2.3l55-95.2H10V-60v-90h-20v90v22.5h-55l55,95.2V60v70l-50-30l60,90l60-90l-50,30V60z M-30,0c0-16.6,13.4-30,30-30S30-16.6,30,0S16.6,30,0,30S-30,16.6-30,0z" :
                            "M10,60v-0.8C38.4,54.4,60,29.7,60,0S38.4-54.4,10-59.2V-60v-90h-20v90v0.8C-38.4-54.4-60-29.7-60,0s21.6,54.4,50,59.2V60v70l-50-30l60,90l60-90l-50,30V60z M-40,0c0-22.1,17.9-40,40-40S40-22.1,40,0S22.1,40,0,40S-40,22.1-40,0z"
                        ),
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
                                    self.selectedStation.fromNow = moment.unix(self.selectedStation.last._id).fromNow();
                                    var status = utils.getStationStatus(self.selectedStation);
                                    self.selectedStation.fromNowClass = utils.getStatusClass(status);
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
                var params = {
                    proj: [
                        'short', 'loc', 'status', 'prov', 'alt', 'last._id', 'last.w-dir', 'last.w-avg', 'last.w-max',
                        'peak'
                    ]
                };
                if (bounds) {
                    params['within-pt1-lat'] = bounds.getNorthEast().lat();
                    params['within-pt1-lon'] = bounds.getNorthEast().lng();
                    params['within-pt2-lat'] = bounds.getSouthWest().lat();
                    params['within-pt2-lon'] = bounds.getSouthWest().lng();
                }
                params.search = self.search;
                params.limit = 100;

                $http({
                    method: 'GET',
                    url: '/api/2/stations/',
                    params: params
                }).success(displayMarkers);
            }

            this.getHistoric = function () {
                var params = {
                    duration: 3600,
                    proj: ['w-dir', 'w-avg']
                };
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + self.selectedStation._id + '/historic',
                    params: params
                }).success(function (data) {
                    var historic = {
                        data: data
                    };
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
                streetViewControl: false,
                mapTypeControlOptions: {
                    mapTypeIds: [google.maps.MapTypeId.TERRAIN, google.maps.MapTypeId.ROADMAP,
                        google.maps.MapTypeId.SATELLITE],
                    position: google.maps.ControlPosition.RIGHT_BOTTOM
                },
                mapTypeId: google.maps.MapTypeId.TERRAIN
            };
            this.map = new google.maps.Map(document.getElementById('map-canvas'), mapOptions);
            google.maps.event.addListener(self.map, 'click', function () {
                if (infoBox) {
                    infoBox.close();
                    self.selectedStation = null;
                }
            });
            google.maps.event.addListener(self.map, 'bounds_changed', (function () {
                var timer;
                return function () {
                    clearTimeout(timer);
                    timer = setTimeout(function () {
                        self.doSearch();
                    }, 500);
                }
            }()));

            $scope.onFromNowInterval = function() {
                if (self.selectedStation) {
                    self.selectedStation.fromNow = moment.unix(self.selectedStation.last._id).fromNow();
                    var status = utils.getStationStatus(self.selectedStation);
                    self.selectedStation.fromNowClass = utils.getStatusClass(status);
                }
            };
            $scope.onRefreshInterval = function() {
                self.doSearch();
                if (self.selectedStation) {
                    self.getHistoric();
                }
            };

            $scope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
                if (toState.name === 'map') {
                    $scope.fromNowInterval = $interval($scope.onFromNowInterval, utils.fromNowInterval);
                    $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
                } else if (fromState.name === 'map') {
                    $interval.cancel($scope.fromNowInterval);
                    $interval.cancel($scope.refreshInterval);
                }
                // Force modal to close on browser back
                $('#detailModal').modal('hide');
            });

            $scope.fromNowInterval = $interval($scope.onFromNowInterval, utils.fromNowInterval);
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
                // Force highcharts to resize
                $('.wdm-wind-chart').highcharts().reflow();
                var params = {
                    duration: 432000,
                    proj: ['w-dir', 'w-avg', 'w-max']
                };
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + $stateParams.stationId + '/historic',
                    params: params
                }).success(function (data) {
                    self.stationWindChart = data;
                });
            });
            $('a[data-target="#tab3"]').on('shown.bs.tab', function (event) {
                // Force highcharts to resize
                $('.wdm-air-chart').highcharts().reflow();
                var params = {
                    duration: 432000,
                    proj: ['temp', 'hum', 'rain']
                };
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + $stateParams.stationId + '/historic',
                    params: params
                }).success(function (data) {
                    self.stationAirChart = data;
                });
            });

            this.getStation = function () {
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + $stateParams.stationId
                }).success(function (data) {
                    self.station = data;
                    self.station.fromNow = moment.unix(self.station.last._id).fromNow();
                    var status = utils.getStationStatus(self.station);
                    self.station.fromNowClass = utils.getStatusClass(status);
                });
            };
            this.getStationHistoric = function () {
                var params = {
                    duration: 3600,
                    proj: ['w-dir', 'w-avg', 'w-max']
                };
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + $stateParams.stationId + '/historic',
                    params: params
                }).success(function (data) {
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

            $scope.onFromNowInterval = function() {
                self.station.fromNow = moment.unix(self.station.last._id).fromNow();
                var status = utils.getStationStatus(self.station);
                self.station.fromNowClass = utils.getStatusClass(status);
            };
            $scope.onRefreshInterval = function() {
                self.doDetail();
            };

            $scope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
                if (toState.name.indexOf('detail') > -1) {
                    $scope.fromNowInterval = $interval($scope.onFromNowInterval, utils.fromNowInterval);
                    $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
                } else if (fromState.name.indexOf('detail') > -1) {
                    $interval.cancel($scope.fromNowInterval);
                    $interval.cancel($scope.refreshInterval);
                }
            });

            $scope.fromNowInterval = $interval($scope.onFromNowInterval, utils.fromNowInterval);
            $scope.refreshInterval = $interval($scope.onRefreshInterval, utils.refreshInterval);
            this.doDetail();
        }]);