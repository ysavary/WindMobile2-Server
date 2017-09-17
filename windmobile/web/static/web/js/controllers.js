var $ = require('jquery/dist/jquery.js');
var angular = require('angular');
var moment = require('moment');
var InfoBox = require('google-maps-infobox');
var _unionBy = require('lodash/unionBy');

var LocationEnum = {
    FIXED: 2,
    SEARCHING: 1,
    SELECTION_MOVED: 0,
    NOT_FIXED: -1,
    DISABLED: -2
};

angular.module('windmobile.controllers', ['windmobile.services'])

    .controller('AppController', ['$scope', '$state', '$stateParams', '$window', '$http', '$translate', 'utils', 'appConfig',
        function ($scope, $state, $stateParams, $window, $http, $translate, utils, appConfig) {
            var self = this;

            this.getGeoLocation = function () {
                if (navigator.geolocation) {
                    self.location = LocationEnum.SEARCHING;
                    navigator.geolocation.getCurrentPosition(function (position) {
                        self.location = LocationEnum.FIXED;
                        self.lat = position.coords.latitude;
                        self.lon = position.coords.longitude;
                        $scope.$broadcast('geoLocation', position.coords.latitude, position.coords.longitude);
                    }, function (positionError) {
                        self.lat = undefined;
                        self.lon = undefined;
                        if (positionError.code === 1) {
                            self.location = LocationEnum.DISABLED;
                            if (!self.locationMsg) {
                                self.locationMsg = true;
                                $translate('Location service is disabled').then(function (text) {
                                    $('.mdl-js-snackbar')[0].MaterialSnackbar.showSnackbar({message: text});
                                });
                            }
                        } else {
                            self.location = LocationEnum.NOT_FIXED;
                            if (!self.locationMsg) {
                                self.locationMsg = true;
                                $translate('Unable to find your location').then(function (text) {
                                    $('.mdl-js-snackbar')[0].MaterialSnackbar.showSnackbar({message: text});
                                });
                            }
                        }
                    }, {
                        enableHighAccuracy: true,
                        maximumAge: 300000,
                        timeout: 20000
                    });
                } else {
                    self.location = LocationEnum.DISABLED;
                }
            };
            this.getProfile = function () {
                var token = $window.localStorage.getItem('token');
                if (token) {
                    $http({
                        method: 'GET',
                        url: '/api/2/users/profile/',
                        headers: {'Authorization': 'JWT ' + token}
                    }).then(function (response) {
                        var data = response.data;
                        var profile;
                        if (data._id.indexOf('facebook-') > -1) {
                            profile = {
                                name: data['user-info'].first_name,
                                picture: "https://graph.facebook.com/" + data['user-info'].id + "/picture"
                            };
                        } else if (data._id.indexOf('google-') > -1) {
                            profile = {
                                name: data['user-info'].given_name,
                                picture: data['user-info'].picture
                            };
                        } else {
                            profile = {
                                name: data._id
                            };
                        }
                        profile.favorites = data.favorites || [];
                        self.profile = profile;
                        $scope.$broadcast('profile');
                    }, function (response) {
                        $window.localStorage.removeItem('token');
                        self.profile = undefined;
                    });
                } else {
                    self.profile = undefined;
                }
            };
            this.toogleFavorite = function(stationId, event) {
                // Prevent opening detail view
                event.stopImmediatePropagation();

                if (stationId) {
                    var token = $window.localStorage.getItem('token');
                    if (token) {
                        if (self.profile.favorites.indexOf(stationId) > -1) {
                            $http({
                                method: 'DELETE',
                                url: '/api/2/users/profile/favorites/' + stationId + '/',
                                headers: {'Authorization': 'JWT ' + token, 'Content-Type': 'application/json'}
                            }).then(function (response) {
                                self.getProfile();
                            }, function (response) {
                                if (response.status === 401) {
                                    $state.go('social-login');
                                }
                            });
                        } else {
                            $http({
                                method: 'POST',
                                url: '/api/2/users/profile/favorites/' + stationId + '/',
                                headers: {'Authorization': 'JWT ' + token, 'Content-Type': 'application/json'}
                            }).then(function (response) {
                                self.getProfile();
                            }, function (response) {
                                if (response.status === 401) {
                                    $state.go('social-login');
                                }
                            });
                        }
                    } else {
                        $state.go('social-login');
                    }
                }
            };

            this.clickOnNavBar = function () {
                if (!utils.inIframe()) {
                    if (['map', 'list'].indexOf($state.current.name) != -1) {
                        $state.go($state.current, {lat: undefined, lon: undefined, zoom: undefined}, {reload: true});
                    } else {
                        $state.go('map');
                    }
                } else {
                    window.open(appConfig.url_absolute);
                }
            };
            this.clickOnHelp = function () {
                console.log('clickOnHelp()');
                if (!utils.inIframe()) {
                    $state.go('help');
                } else {
                    window.open(appConfig.url_absolute + '/stations/help');
                }
            };

            this.logout = function () {
                $window.localStorage.removeItem('token');
                $state.go($state.current, {}, {reload: true});
            };

            this.getGeoLocation();
            this.getProfile();
        }
    ])

    .controller('ListController',
        ['$scope', '$state', '$http', '$location', '$q', 'utils', 'lat', 'lon',
            function ($scope, $state, $http, $location, $q, utils, lat, lon) {
                var self = this;

                function search() {
                    var keys = ['short', 'loc', 'status', 'pv-name', 'alt', 'last._id', 'last.w-dir', 'last.w-avg',
                        'last.w-max'];

                    var nbFavorites = 0;
                    if ($scope.$app.profile && $scope.$app.profile.favorites && $scope.$app.profile.favorites.length > 0) {
                        nbFavorites = $scope.$app.profile.favorites.length;
                        var favoritesParam = {
                            keys: keys
                        };
                        if (self.tenant) {
                            favoritesParam.provider = self.tenant;
                        }
                        favoritesParam.search = self.search;
                        favoritesParam.limit = 30;
                        favoritesParam.ids = $scope.$app.profile.favorites;
                        var favoritesPromise = $http({
                            method: 'GET',
                            url: '/api/2/stations/',
                            params: favoritesParam
                        });
                    }

                    var hasGeoLoc = self.lat != undefined && self.lon != undefined;
                    if (hasGeoLoc || nbFavorites === 0) {
                        var listParam = {
                            keys: keys
                        };
                        if (hasGeoLoc) {
                            listParam['near-lat'] = self.lat;
                            listParam['near-lon'] = self.lon;
                        }
                        if (self.tenant) {
                            listParam.provider = self.tenant;
                        }
                        listParam.search = self.search;
                        listParam.limit = Math.max(12 - nbFavorites, 3);
                        var listPromise = $http({
                            method: 'GET',
                            url: '/api/2/stations/',
                            params: listParam
                        });
                    }

                    $q.all({
                        'favorites': favoritesPromise || $q.resolve([]),
                        'list': listPromise || $q.resolve([])
                    }).then(function (values) {
                        self.stations = _unionBy(values.favorites.data, values.list.data, function (value) {
                            return value._id;
                        });
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
                this.doSearch = function (lat, lon) {
                    if (lat != undefined && lon != undefined) {
                        self.lat = lat;
                        self.lon = lon;
                    }
                    search();
                };
                this.clearSearch = function () {
                    this.search = null;
                    // https://stackoverflow.com/questions/31638890/mdl-textfield-not-taking-ngmodel-changes-into-account/40781433
                    $('#wdm-search-field-parent').removeClass('is-dirty');
                    $location.search('search', null);
                    this.doSearch();
                };
                this.getGeoStatus = function () {
                    if ($scope.$app.location == LocationEnum.FIXED) {
                        if (self.lat != $scope.$app.lat && self.lon != $scope.$app.lon) {
                            return LocationEnum.SELECTION_MOVED;
                        }
                    }
                    return $scope.$app.location;
                };

                this.updateFromNow = function (station) {
                    if (station.last) {
                        station.fromNow = moment.unix(station.last._id).fromNow();
                        var status = utils.getStationStatus(station);
                        station.fromNowClass = utils.getStatusClass(status);
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
                    // Save list position in $app
                    $scope.$app.listLat = self.lat;
                    $scope.$app.listLon = self.lon;

                    // Force modal to close on browser back
                    $('#detailModal').modal('hide');
                });
                $scope.$on('visibilityChange', function (event, isHidden) {
                    if (!isHidden) {
                        console.info(moment().format() + " --> [ListController] visibilityChange: isHidden=" + isHidden);
                        self.doSearch();
                    }
                });

                $('#wdm-search-field').keydown(function (event) {
                    if (event.keyCode == 13) {
                        this.blur();
                        return false;
                    }
                });

                this.tenant = utils.getTenant($location.host());
                this.search = $location.search().search;

                // lat, lon initiated by ui-router or query parameters
                var initialLat, initialLon;
                var ignoreNextGeolocation = false;
                if (lat != undefined && lon != undefined) {
                    initialLat = lat;
                    initialLon = lon;
                } else if ($location.search().lat && $location.search().lon) {
                    var lat = parseFloat($location.search().lat);
                    var lon = parseFloat($location.search().lon);

                    if (isNaN(lat) || isNaN(lon)) {
                        initialLat = undefined;
                        initialLon = undefined;
                    } else {
                        ignoreNextGeolocation = true;
                        initialLat = lat;
                        initialLon = lon;
                    }
                }

                if (initialLat == undefined && self.lon == undefined) {
                    if ($scope.$app.listLat != undefined && $scope.$app.listLon != undefined) {
                        // Use last map position
                        initialLat = $scope.$app.listLat;
                        initialLon = $scope.$app.listLon;
                    } else if ($scope.$app.lat != undefined && $scope.$app.lon != undefined) {
                        // Use last geolocation
                        initialLat = $scope.$app.lat;
                        initialLon = $scope.$app.lon;
                    }
                }

                $scope.$on('geoLocation', function (event, lat, lon) {
                    if (!ignoreNextGeolocation) {
                        self.doSearch(lat, lon);
                    } else {
                        ignoreNextGeolocation = false;
                    }
                });
                $scope.$on('profile', function (event) {
                    self.doSearch();
                });

                this.doSearch(initialLat, initialLon);
            }
    ])

    .controller('MapController',
        ['$scope', '$state', '$http', '$compile', '$templateCache', '$location', 'utils',
            'lat', 'lon', 'zoom',
        function ($scope, $state, $http, $compile, $templateCache, $location, utils,
                  lat, lon, zoom) {
            var self = this;
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
                    var scale = 0.12;
                    if ($scope.$app.profile && $scope.$app.profile.favorites) {
                        if ($scope.$app.profile.favorites.indexOf(station._id) > -1) {
                            scale = scale + scale * 0.3;
                        }
                    }

                    var icon = {
                        path: (station.peak ?
                            "M20,67.4L88.3-51H20v-99h-40v99h-68.3L-20,67.4V115l-50-25L0,190L70,90l-50,25V67.4z M-35,0c0-19.3,15.7-35,35-35S35-19.3,35,0S19.3,35,0,35S-35,19.3-35,0z" :
                            "M20,67.1C48.9,58.5,70,31.7,70,0S48.9-58.5,20-67.1V-150h-40v82.9C-48.9-58.5-70-31.7-70,0s21.1,58.5,50,67.1V115l-50-25L0,190L70,90l-50,25V67.1z M-35,0c0-19.3,15.7-35,35-35S35-19.3,35,0S19.3,35,0,35S-35,19.3-35,0z"
                        ),
                        scale: scale,
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
            function search(bounds, search) {
                var params = {
                    keys: [
                        'short', 'loc', 'status', 'pv-name', 'alt', 'last._id', 'last.w-dir', 'last.w-avg', 'last.w-max',
                        'peak'
                    ]
                };
                params['within-pt1-lat'] = bounds.getNorthEast().lat();
                params['within-pt1-lon'] = bounds.getNorthEast().lng();
                params['within-pt2-lat'] = bounds.getSouthWest().lat();
                params['within-pt2-lon'] = bounds.getSouthWest().lng();

                // Ask for ~15 markers for 300x300 pixels
                params['limit'] = Math.round($(window).width() * $(window).height() * (15 / 90000));

                if (search) {
                    params['search'] = search;
                }
                if (self.tenant) {
                    params.provider = self.tenant
                }

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
                search(this.map.getBounds(), self.search);
            };
            this.clearSearch = function () {
                this.search = null;
                // https://stackoverflow.com/questions/31638890/mdl-textfield-not-taking-ngmodel-changes-into-account/40781433
                $('#wdm-search-field-parent').removeClass('is-dirty');
                $location.search('search', null);
                this.doSearch();
            };
            this.centerMap = function (lat, lon, zoom) {
                self.map.panTo({
                    lat: lat,
                    lng: lon
                });
                self.map.setZoom(zoom);
            };
            this.getGeoStatus = function () {
                if ($scope.$app.location == LocationEnum.FIXED) {
                    var center = self.map.getCenter();
                    if (center) {
                        if (utils.roundTo3Digits($scope.$app.lat) != utils.roundTo3Digits(center.lat()) &&
                            utils.roundTo3Digits($scope.$app.lon) != utils.roundTo3Digits(center.lng())) {
                            return LocationEnum.SELECTION_MOVED;
                        }
                    }
                }
                return $scope.$app.location;
            };

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

            $scope.$on('$stateChangeStart', function (event, toState, toParams, fromState, fromParams) {
                console.info(moment().format() + " --> [MapController] $stateChangeStart: fromState="
                    + fromState.name + ", toState=" + toState.name);
                // Save map position in $app
                var center = self.map.getCenter();
                $scope.$app.mapLat = center.lat();
                $scope.$app.mapLon = center.lng();
                $scope.$app.mapZoom = self.map.getZoom();

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
            $('#wdm-search-field').keydown(function (event) {
                if (event.keyCode == 13) {
                    this.blur();
                    return false;
                }
            });

            this.tenant = utils.getTenant($location.host());
            this.search = $location.search().search;

            // Initialize Google Maps
            var mapOptions = {
                panControl: false,
                streetViewControl: false,
                mapTypeControlOptions: {
                    mapTypeIds: [google.maps.MapTypeId.TERRAIN, google.maps.MapTypeId.ROADMAP,
                        google.maps.MapTypeId.SATELLITE],
                    position: google.maps.ControlPosition.LEFT_BOTTOM
                },
                mapTypeId: google.maps.MapTypeId.TERRAIN
            };
            this.map = new google.maps.Map($('#wdm-map')[0], mapOptions);

            this.getLegendColorStyle = function (value) {
                return {color: utils.getColorInRange(value, 50)};
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
                var count = 0;
                return function () {
                    count++;
                    // Ignore the n first bounds_changed generated by the map itself
                    if (count > 1) {
                        ignoreNextGeolocation = true;
                    }
                    clearTimeout(timer);
                    timer = setTimeout(function () {
                        self.doSearch();
                    }, 500);
                }
            }()));

            // lat, lon, zoom initiated by ui-router or query parameters
            var initialLat, initialLon, initialZoom;
            var ignoreNextGeolocation = false;
            if (lat != undefined && lon != undefined) {
                initialLat = lat;
                initialLon = lon;
            } else if ($location.search().lat && $location.search().lon) {
                var lat = parseFloat($location.search().lat);
                var lon = parseFloat($location.search().lon);

                if (isNaN(lat) || isNaN(lon)) {
                    initialLat = undefined;
                    initialLon = undefined;
                } else {
                    ignoreNextGeolocation = true;
                    initialLat = lat;
                    initialLon = lon;
                }
            }
            var defaultZoom = 10;
            if (zoom != undefined) {
                initialZoom = zoom;
            } else {
                var zoom = parseInt($location.search().zoom);
                initialZoom = isNaN(zoom) ? defaultZoom : zoom;
            }

            if (initialLat == undefined && self.lon == undefined) {
                if ($scope.$app.mapLat != undefined && $scope.$app.mapLon != undefined) {
                    // Use last map position
                    initialLat = $scope.$app.mapLat;
                    initialLon = $scope.$app.mapLon;
                    initialZoom = $scope.$app.mapZoom;
                } else if ($scope.$app.lat != undefined && $scope.$app.lon != undefined) {
                    // Use last geolocation
                    initialLat = $scope.$app.lat;
                    initialLon = $scope.$app.lon;
                    initialZoom = defaultZoom;
                } else {
                    // France and Switzerland by default
                    initialLat = 46.76;
                    initialLon = 4.08;
                    initialZoom = 6;
                }
            }

            $scope.$on('geoLocation', function (event, lat, lon) {
                if (!ignoreNextGeolocation) {
                    self.centerMap(lat, lon, defaultZoom);
                } else {
                    ignoreNextGeolocation = false;
                }
            });

            // Should try to find another way to reload map when the #wdm-map change
            setTimeout(function () {
                var center = self.map.getCenter();
                google.maps.event.trigger(self.map, 'resize');
                self.map.setCenter(center);
            }, 500);

            this.centerMap(initialLat, initialLon, initialZoom);
        }
    ])

    .controller('DetailController',
        ['$scope', '$state', '$stateParams', '$http', '$window', 'utils',
        function ($scope, $state, $stateParams, $http, $window, utils) {
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
                    var time = moment.unix(self.station.last._id);
                    self.station.fromNow = time.fromNow();
                    var status = utils.getStationStatus(self.station);
                    self.station.fromNowClass = utils.getStatusClass(status);
                    self.station.updateTime = time.format('lll');
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

            this.showOnMap = function (station) {
                $state.go('map', {
                    lat: station.loc.coordinates[1], lon: station.loc.coordinates[0],
                    zoom: 10
                });
            };
            this.showOnList = function (station) {
                $state.go('list', {
                    lat: station.loc.coordinates[1], lon: station.loc.coordinates[0]
                });
            };

            this.doDetail();
        }
    ])

    .controller('SocialLoginController', ['$state', 'utils', 'appConfig',
        function ($state, utils, appConfig) {
            this.clickOnNavBar = function () {
                if (!utils.inIframe()) {
                    $state.go('map');
                } else {
                    window.open(appConfig.url_absolute);
                }
            };
        }
    ])

    .controller('LoginController', ['$scope', '$http', '$state', '$window', '$translate', 'utils', 'appConfig',
        function ($scope, $http, $state, $window, $translate, utils, appConfig) {
            var self = this;

            this.login = function () {
                if (!self.username) {
                    $translate('Username is empty').then(function (text) {
                        self.usernameError = text;
                    });
                } else {
                    self.usernameError = undefined;
                }
                if (!self.password) {
                    $translate('Password is empty').then(function (text) {
                        self.passwordError = text;
                    });
                } else {
                    self.passwordError = undefined;
                }

                if (self.username && self.password) {
                    $http({
                        method: 'POST',
                        url: '/api/2/auth/login/',
                        data: {
                            username: self.username,
                            password: self.password
                        }
                    }).then(function (response) {
                        $window.localStorage.token = response.data.token;
                        $state.go('list');
                    }, function (response) {
                        $translate('Invalid username or password').then(function (text) {
                            self.passwordError = text;
                        });
                    })
                }
            };
            this.clickOnNavBar = function () {
                if (!utils.inIframe()) {
                    $state.go('map');
                } else {
                    window.open(appConfig.url_absolute);
                }
            };

            $scope.$watch('$ctrl.usernameError', function (newVal, oldVal) {
                $('#username-error').css('visibility', self.usernameError ? 'visible' : 'hidden');
            });
            $scope.$watch('$ctrl.passwordError', function (newVal, oldVal) {
                $('#password-error').css('visibility', self.passwordError ? 'visible' : 'hidden');
            });
        }
    ])

    .controller('HelpController', ['$state', '$anchorScroll', '$sce', '$translate', 'utils',
        function ($state, $anchorScroll, $sce, $translate, utils) {
            var self = this;

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
            }],
            fromNow: moment().add(-1, 'hours').fromNow()
            };
            this.getLegendColorStyle = function(value) {
                return {background: utils.getColorInRange(value, 50)};
            };
            (function () {
                $translate('HELP_FAVORITES_TEXT_1').then(function (text) {
                    text = text.replace('[[facebookLink]]', '<a href="/auth/facebook/oauth2callback/">Facebook</a>');
                    text = text.replace('[[googleLink]]', '<a href="/auth/google/oauth2callback/">Google</a>');
                    self.favoritesText1 = $sce.trustAsHtml(text);
                });
            })();
            setTimeout(function () {
                $anchorScroll();
            }, 300);
        }
    ]);
