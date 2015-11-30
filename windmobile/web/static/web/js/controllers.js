var angular = require('angular');
var moment = require('moment');
var InfoBox = require('google-maps-infobox');
require('ng-toast');

angular.module('windmobile.controllers', ['ngToast', 'windmobile.services'])

    .controller('ListController', ['$scope', '$state', '$http', '$location', 'utils',
        function ($scope, $state, $http, $location, utils) {
            var self = this;

            function search(position) {
                var params = {
                    keys: ['short', 'loc', 'status', 'pv-name', 'alt', 'last._id', 'last.w-dir', 'last.w-avg', 'last.w-max']
                };
                if (position) {
                    params['near-lat'] = position.coords.latitude;
                    params['near-lon'] = position.coords.longitude;
                }
                if (self.tenant) {
                    params.provider = self.tenant
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
                        if (station.last) {
                            self.updateFromNow(station);
                            self.getHistoric(station);
                        }
                    }
                });
            }
            this.getHistoric = function (station) {
                var params = {
                    duration: 3600,
                    keys: ['w-dir', 'w-avg']
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
                    // If the user does not answer the geolocation request, the error handler will never be called even
                    // with a timeout option
                    var locationTimeout = setTimeout(search, 1000);
                    navigator.geolocation.getCurrentPosition(function (position) {
                        clearTimeout(locationTimeout);
                        search(position);
                    }, function (positionError) {
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
            this.updateFromNow = function(station) {
                if (station.last) {
                    station.fromNow = moment.unix(station.last._id).fromNow();
                    var status = utils.getStationStatus(station);
                    station.fromNowClass = utils.getStatusClass(status);
                }
            };
            this.clickOnNavBar = function() {
                if (!utils.inIframe()) {
                    self.clearSearch();
                } else {
                    window.open('http://winds.mobi');
                }
            };

            $scope.$on('onFromNowInterval', function () {
                for (var i = 0; i < self.stations.length; i++) {
                    self.updateFromNow(self.stations[i]);
                }
            });
            $scope.$on('onRefreshInterval', function () {
                console.info(moment().format() + " --> [ListController] onRefreshInterval");
                self.doSearch();
            });
            $scope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
                console.info(moment().format() + " --> [ListController] $stateChangeStart: fromState=" + fromState.name);
                // Force modal to close on browser back
                $('#detailModal').modal('hide');
            });
            $scope.$on('visibilityChange', function(event, isHidden) {
                if (!isHidden) {
                    console.info(moment().format() + " --> [ListController] visibilityChange: isHidden=" + isHidden);
                    self.doSearch();
                }
            });

            this.tenant = utils.getTenant($location.host());
            this.search = $location.search().search;
            this.doSearch();
        }])

    .controller('MapController', ['$rootScope', '$scope', '$state', '$http', '$compile', '$translate', '$templateCache', '$location', 'ngToast', 'utils',
        function ($rootScope, $scope, $state, $http, $compile, $translate, $templateCache, $location, ngToast, utils) {
            var self = this;

            ngToast.settings.maxNumber = 1;
            var infoBox;

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
                            self.updateFromNow();
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
                                        self.updateFromNow();
                                        self.getHistoric();
                                    }

                                    infoBox = new InfoBox({
                                        content: $compile($templateCache.get('_infobox.html'))($scope)[0],
                                        closeBoxURL: '',
                                        /* same media query as right-margin in windmobile.scss */
                                        infoBoxClearance: (window.matchMedia('(min-width: 400px)').matches ?
                                            new google.maps.Size(60, 0) : new google.maps.Size(50, 0))
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
                    keys: [
                        'short', 'loc', 'status', 'pv-name', 'alt', 'last._id', 'last.w-dir', 'last.w-avg', 'last.w-max',
                        'peak'
                    ]
                };
                if (bounds) {
                    params['within-pt1-lat'] = bounds.getNorthEast().lat();
                    params['within-pt1-lon'] = bounds.getNorthEast().lng();
                    params['within-pt2-lat'] = bounds.getSouthWest().lat();
                    params['within-pt2-lon'] = bounds.getSouthWest().lng();
                }
                if (self.tenant) {
                    params.provider = self.tenant
                }
                params.search = self.search;
                // 1000*1000 px windows should have a limit ~= 100
                params.limit = Math.round($(window).width() * $(window).height() / (1000 * 1000 / 100));

                $http({
                    method: 'GET',
                    url: '/api/2/stations/',
                    params: params
                }).success(displayMarkers);
            }

            this.getHistoric = function () {
                var params = {
                    duration: 3600,
                    keys: ['w-dir', 'w-avg']
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
                $location.search('search', null);
                this.doSearch();
            };
            this.centerMap = function () {
                if (navigator.geolocation) {
                    $('#center-map').addClass('wdm-navbar-button-active');
                    navigator.geolocation.getCurrentPosition(function (position) {
                        var currentPosition = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
                        self.map.panTo(currentPosition);
                        self.map.setZoom(8);
                        //search(currentPosition);
                        $('#center-map').removeClass('wdm-navbar-button-active');
                    }, function (positionError) {
                        $('#center-map').removeClass('wdm-navbar-button-active');
                        if (positionError.code > 1) {
                            $translate('Unable to find your location').then(function (text) {
                                ngToast.create({
                                    className: 'alert alert-danger',
                                    content: text
                                });
                            });
                        }
                    }, {
                        enableHighAccuracy: true,
                        maximumAge: 300000,
                        timeout: 20000
                    });
                }
            };
            this.clickOnNavBar = function() {
                if (!utils.inIframe()) {
                    self.clearSearch();
                } else {
                    window.open('http://winds.mobi');
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
            this.updateFromNow = function() {
                if (self.selectedStation && self.selectedStation.last) {
                    self.selectedStation.fromNow = moment.unix(self.selectedStation.last._id).fromNow();
                    var status = utils.getStationStatus(self.selectedStation);
                    self.selectedStation.fromNowClass = utils.getStatusClass(status);
                }
            };

            $scope.$on('onFromNowInterval', function() {
                self.updateFromNow();
            });
            $scope.$on('onRefreshInterval', function() {
                console.info(moment().format() + " --> [MapController] onRefreshInterval");
                self.doSearch();
                if (self.selectedStation) {
                    self.getHistoric();
                }
            });
            $rootScope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
                console.info(moment().format() + " --> [MapController] $stateChangeStart: fromState="
                    + fromState.name + ", toState=" + toState.name);
                // Force modal to close on browser back
                $('#detailModal').modal('hide');
            });
            $scope.$on('visibilityChange', function(event, isHidden) {
                if (!isHidden) {
                    console.info(moment().format() + " --> [MapController] visibilityChange: isHidden=" + isHidden);
                    self.doSearch();
                    if (self.selectedStation) {
                        self.getHistoric();
                    }
                }
            });

            this.tenant = utils.getTenant($location.host());
            this.search = $location.search().search;
            this.centerMap();
        }])

    .controller('DetailController', ['$rootScope', '$scope', '$state', '$stateParams', '$http', 'utils',
        function ($rootScope, $scope, $state, $stateParams, $http, utils) {
            var self = this;

            $('#detailModal').modal().on('hidden.bs.modal', function (e) {
                $state.go('^');
            });

            $('a[data-target="#tab2"]').on('shown.bs.tab', function (event) {
                // Force highcharts to resize
                $('.wdm-wind-chart').highcharts().reflow();
                var params = {
                    duration: 432000,
                    keys: ['w-dir', 'w-avg', 'w-max']
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
                    keys: ['temp', 'hum', 'rain']
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
                    self.updateFromNow();
                });
            };
            this.getStationHistoric = function () {
                var params = {
                    duration: 3600,
                    keys: ['w-dir', 'w-avg', 'w-max']
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
            this.updateFromNow = function() {
                if (self.station.last) {
                    self.station.fromNow = moment.unix(self.station.last._id).fromNow();
                    var status = utils.getStationStatus(self.station);
                    self.station.fromNowClass = utils.getStatusClass(status);
                }
            };

            $scope.$on('onFromNowInterval', function() {
                self.updateFromNow();
            });
            $scope.$on('onRefreshInterval', function() {
                console.info(moment().format() + " --> [DetailController] onRefreshInterval");
                self.doDetail();
            });
            $scope.$on('visibilityChange', function(event, isHidden) {
                if (!isHidden) {
                    console.info(moment().format() + " --> [DetailController] visibilityChange: isHidden=" + isHidden);
                    self.doDetail();
                }
            });

            this.doDetail();
        }])

    .controller('HelpController', ['$state', 'utils',
        function ($state, utils) {
            this.example = {
                data: [{
                    "_id": 1444993200,
                    "w-dir": 305,
                    "w-avg": 10.2,
                    "w-max": 20.4
                }, {
                    "_id": 1444992600,
                    "w-dir": 288,
                    "w-avg": 11.3,
                    "w-max": 25.2
                }, {
                    "_id": 1444992000,
                    "w-dir": 255,
                    "w-avg": 6.9,
                    "w-max": 18.7
                }, {
                    "_id": 1444991400,
                    "w-dir": 267,
                    "w-avg": 4.9,
                    "w-max": 17.1
                }, {
                    "_id": 1444990800,
                    "w-dir": 204,
                    "w-avg": 5,
                    "w-max": 13.0
                }, {
                    "_id": 1444990200,
                    "w-dir": 213,
                    "w-avg": 4.0,
                    "w-max": 11.3
                }, {
                    "_id": 1444989600,
                    "w-dir": 184,
                    "w-avg": 6.1,
                    "w-max": 13.1
                }, {
                    "_id": 1444989000,
                    "w-dir": 172,
                    "w-avg": 5.8,
                    "w-max": 13.2
                }
                ]
            };
            this.getLegendColor = function(value) {
                return utils.getColorInRange(value, 50);
            };
            this.clickOnNavBar = function () {
                if (!utils.inIframe()) {
                    $state.go('map');
                } else {
                    window.open('http://winds.mobi');
                }
            };
        }])

    .controller('MyListController', ['$scope', '$state', '$http', '$location', '$window', 'utils',
        function ($scope, $state, $http, $location, $window, utils) {
            var self = this;

            function search(favorites) {
                var params = {
                    keys: ['short', 'loc', 'status', 'pv-name', 'alt', 'last._id', 'last.w-dir', 'last.w-avg', 'last.w-max']
                };
                if (self.tenant) {
                    params.provider = self.tenant
                }
                params.ids = favorites;
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
                        if (station.last) {
                            self.updateFromNow(station);
                            self.getHistoric(station);
                        }
                    }
                });
            }
            this.getHistoric = function (station) {
                var params = {
                    duration: 3600,
                    keys: ['w-dir', 'w-avg']
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
                $state.go('my-list.detail', {stationId: station._id});
            };
            this.doSearch = function () {
                if (self.favorites && self.favorites.length > 0) {
                    search(self.favorites);
                }
            };
            this.clearSearch = function () {
                this.search = null;
                $location.search('search', null);
                this.doSearch();
            };
            this.updateFromNow = function(station) {
                if (station.last) {
                    station.fromNow = moment.unix(station.last._id).fromNow();
                    var status = utils.getStationStatus(station);
                    station.fromNowClass = utils.getStatusClass(status);
                }
            };
            this.clickOnNavBar = function() {
                if (!utils.inIframe()) {
                    self.clearSearch();
                } else {
                    window.open('http://winds.mobi');
                }
            };

            $scope.$on('onFromNowInterval', function () {
                for (var i = 0; i < self.stations.length; i++) {
                    self.updateFromNow(self.stations[i]);
                }
            });
            $scope.$on('onRefreshInterval', function () {
                console.info(moment().format() + " --> [ListController] onRefreshInterval");
                self.doSearch();
            });
            $scope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
                console.info(moment().format() + " --> [ListController] $stateChangeStart: fromState=" + fromState.name);
                // Force modal to close on browser back
                $('#detailModal').modal('hide');
            });
            $scope.$on('visibilityChange', function(event, isHidden) {
                if (!isHidden) {
                    console.info(moment().format() + " --> [ListController] visibilityChange: isHidden=" + isHidden);
                    self.doSearch();
                }
            });

            this.tenant = utils.getTenant($location.host());
            this.search = $location.search().search;

            var token = $window.localStorage.token;
            if (token) {
                $http({
                    method: 'GET',
                    url: '/api/2/users/profile/',
                    headers: {'Authorization': 'JWT ' + token}
                }).then(function (response) {
                    self.favorites = response.data.favorites;
                    self.doSearch();
                }, function () {
                    $state.go('my-list.login');
                });
            } else {
                $state.go('my-list.login');
            }
        }])

    .controller('LoginController', ['$http', '$state', '$window',
        function ($http, $state, $window) {
            var self = this;

            $('#loginModal').modal().on('hidden.bs.modal', function (e) {
                $state.go('^');
            });

            this.login = function () {
                $http({
                    method: 'POST',
                    url: '/api/2/auth/login/',
                    data: {
                        username: self.username,
                        password: self.password
                    }
                }).then(function (response) {
                    $window.localStorage.token = response.data.token;
                    $state.go('my-list');
                }, function (response) {
                    console.log(response.data);
                })
            }
        }]);
