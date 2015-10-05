var angular = require('angular');
var moment = require('moment');
var InfoBox = require('google-maps-infobox');

angular.module('windmobile.controllers', ['windmobile.services'])

    .controller('ListController', ['$scope', '$state', '$http', '$interval', '$location', 'utils',
        function ($scope, $state, $http, $interval, $location, utils) {
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
                    url: 'http://winds.mobi/api/2/stations/',
                    params: params
                }).success(function (data) {
                    self.stations = data;
                    for (var i = 0; i < self.stations.length; i++) {
                        var station = self.stations[i];
                        if (station.last) {
                            station.fromNow = moment.unix(station.last._id).fromNow();
                            var status = utils.getStationStatus(station);
                            station.fromNowClass = utils.getStatusClass(status);
                            self.getHistoric(station);
                        }
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
                    url: 'http://winds.mobi/api/2/stations/' + station._id + '/historic',
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
                    navigator.geolocation.getCurrentPosition(function (position) {
                        clearTimeout(locationTimeout);
                        search(position);
                    }, function (error) {
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
                $location.search('search', null);
                this.doSearch();
            };

            $scope.onFromNowInterval = function () {
                for (var i = 0; i < self.stations.length; i++) {
                    var station = self.stations[i];
                    if (station.last) {
                        station.fromNow = moment.unix(station.last._id).fromNow();
                        var status = utils.getStationStatus(station);
                        station.fromNowClass = utils.getStatusClass(status);
                    }
                }
            };
            $scope.onRefreshInterval = function () {
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

            this.search = $location.search().search;
            this.doSearch();
        }])

    .controller('MapController', ['$scope', '$state', '$http', '$compile', '$templateCache', '$interval', '$location', 'utils',
        function ($scope, $state, $http, $compile, $templateCache, $interval, $location, utils) {
            var infoBox;

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
                        if (self.selectedStation.last) {
                            self.selectedStation.fromNow = moment.unix(self.selectedStation.last._id).fromNow();
                            var status = utils.getStationStatus(self.selectedStation);
                            self.selectedStation.fromNowClass = utils.getStatusClass(status);
                            self.getHistoric();
                        }
                    }

                    var color;
                    if (utils.getStationStatus(station) == 0) {
                        color = utils.getColorInRange(-1);
                    } else {
                        color = utils.getColorInRange(station.last['w-max'], 50);
                    }
                    var icon = {
                        path: (station.peak ?
                            "M20,67.4L88.3-51H20v-99h-40v99h-68.3L-20,67.4V115l-50-25L0,190L70,90l-50,25V67.4z M-35,0c0-19.3,15.7-35,35-35S35-19.3,35,0S19.3,35,0,35S-35,19.3-35,0z" :
                            "M20,67.1C48.9,58.5,70,31.7,70,0S48.9-58.5,20-67.1V-150h-40v82.9C-48.9-58.5-70-31.7-70,0s21.1,58.5,50,67.1V115l-50-25L0,190L70,90l-50,25V67.1z M-35,0c0-19.3,15.7-35,35-35S35-19.3,35,0S19.3,35,0,35S-35,19.3-35,0z"
                        ),
                        scale: 0.12,
                        fillOpacity: 1,
                        fillColor: color,
                        strokeWeight: 0,
                        rotation: (station.last ? station.last['w-dir'] : 0)
                    };

                    if (!marker) {
                        marker = new google.maps.Marker({
                            title: station['short'],
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
                                    if (self.selectedStation.last) {
                                        self.selectedStation.fromNow = moment.unix(self.selectedStation.last._id).fromNow();
                                        var status = utils.getStationStatus(self.selectedStation);
                                        self.selectedStation.fromNowClass = utils.getStatusClass(status);
                                        self.getHistoric();
                                    }

                                    infoBox = new InfoBox({
                                        content: $compile($templateCache.get('_infobox.html'))($scope)[0],
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
                    url: 'http://winds.mobi/api/2/stations/',
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
                    url: 'http://winds.mobi/api/2/stations/' + self.selectedStation._id + '/historic',
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
                $location.search('search', null);
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
                    position: google.maps.ControlPosition.LEFT_BOTTOM
                },
                mapTypeId: google.maps.MapTypeId.TERRAIN
            };
            this.map = new google.maps.Map(document.getElementById('map-canvas'), mapOptions);

            this.getLegendColor = function(value) {
                return utils.getColorInRange(value, 50);
            };
            var legendDiv = $compile($templateCache.get('_legend.html'))($scope);
            this.map.controls[google.maps.ControlPosition.RIGHT_CENTER].push(legendDiv[0]);

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
                    if (self.selectedStation.last) {
                        self.selectedStation.fromNow = moment.unix(self.selectedStation.last._id).fromNow();
                        var status = utils.getStationStatus(self.selectedStation);
                        self.selectedStation.fromNowClass = utils.getStatusClass(status);
                    }
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

            this.search = $location.search().search;
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
                    url: 'http://winds.mobi/api/2/stations/' + $stateParams.stationId + '/historic',
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
                    url: 'http://winds.mobi/api/2/stations/' + $stateParams.stationId + '/historic',
                    params: params
                }).success(function (data) {
                    self.stationAirChart = data;
                });
            });

            this.getStation = function () {
                $http({
                    method: 'GET',
                    url: 'http://winds.mobi/api/2/stations/' + $stateParams.stationId
                }).success(function (data) {
                    self.station = data;
                    if (self.station.last) {
                        self.station.fromNow = moment.unix(self.station.last._id).fromNow();
                        var status = utils.getStationStatus(self.station);
                        self.station.fromNowClass = utils.getStatusClass(status);
                    }
                });
            };
            this.getStationHistoric = function () {
                var params = {
                    duration: 3600,
                    proj: ['w-dir', 'w-avg', 'w-max']
                };
                $http({
                    method: 'GET',
                    url: 'http://winds.mobi/api/2/stations/' + $stateParams.stationId + '/historic',
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
                if (self.station.last) {
                    self.station.fromNow = moment.unix(self.station.last._id).fromNow();
                    var status = utils.getStationStatus(self.station);
                    self.station.fromNowClass = utils.getStatusClass(status);
                }
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