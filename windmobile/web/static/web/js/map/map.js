angular.module('windMobile.map', ['ngRoute', 'ngMap'])

    .config(['$routeProvider', function ($routeProvider) {
        $routeProvider.when('/map', {
            templateUrl: '/static/web/js/map/map.html',
            controller: 'MapController'
        });
    }])

    .controller('MapController', ['$scope', '$http', '$compile', '$templateCache', function ($scope, $http, $compile, $templateCache) {
        var markersArray = [];
        var infoBox = null;

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

            var element = $compile($templateCache.get('_infobox.html'))($scope);

            for (var i = 0; i < stations.length; i++) {
                var station = stations[i];

                if ((station.status == "green") && (station.last)) {
                    var position = new google.maps.LatLng(station.loc.coordinates[1], station.loc.coordinates[0]);
                    var windMax = station.last['w-max'];

                    var color;
                    if (windMax === undefined) {
                        color = 'DarkGray'
                    } else if (windMax >= 0 && windMax < 10) {
                        color = 'MediumAquaMarine';
                    } else if (windMax >= 10 && windMax < 20) {
                        color = 'SeaGreen'
                    } else if (windMax >= 20 && windMax < 25) {
                        color = 'DarkCyan'
                    } else if (windMax >= 25 && windMax < 30) {
                        color = 'MediumSlateBlue'
                    } else if (windMax >= 30 && windMax < 35) {
                        color = 'BlueViolet'
                    } else if (windMax >= 35 && windMax < 40) {
                        color = 'OrangeRed'
                    } else if (windMax >= 40) {
                        color = 'Crimson'
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
                        position: position,
                        icon: icon,
                        map: $scope.map
                    });
                    marker.station = station;
                    markersArray.push(marker);

                    /*
                     $scope.station = null;
                     $scope.historic = [];
                     var element = $compile(content)($scope);
                     */

                    (function (marker) {
                        google.maps.event.addListener(marker, 'click', function () {
                            if (infoBox) {
                                infoBox.close();
                            }
                            $scope.station = marker.station;
                            $scope.getHistoric();
                            infoBox = new InfoBox({
                                content: element[0]
                            });
                            infoBox.open($scope.map, marker);
                        })
                    })(marker);
                }
            }
        }

        $scope.getHistoric = function () {
            $http({method: 'GET', url: '/api/2/stations/' + $scope.station._id + '/historic?duration=3600'})
                .success(function (data) {
                    $scope.historic = data;

                    var miniChartData = '';
                    var count = data.length;
                    for (var i = count - 1; i >= 0; i--) {
                        miniChartData += data[i]['_id'] + ':' + data[i]['w-avg'];
                        if (i > 0) {
                            miniChartData += ',';
                        }
                    }
                    $scope.miniChartData = miniChartData;
                })
                .error(function () {
                   $scope.historic = [];
                })
        };

        $scope.geoSearch = function (position) {
            var currentPosition = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
            $scope.map.setCenter(currentPosition);

            var params = {};
            params.lat = position.coords.latitude;
            params.lon = position.coords.longitude;
            params.limit = 1000;

            $http({method: 'GET', url: '/api/2/stations/', params: params}).success(displayMarkers);
        };

        $scope.search = function () {
            var params = {};
            params.search = $scope.query;
            params.limit = 1000;
            $http({method: 'GET', url: '/api/2/stations/', params: params}).success(displayMarkers);
        };

        $scope.getGeoLocation = function () {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition($scope.geoSearch, $scope.search, {
                    enableHighAccuracy: true,
                    timeout: 3000,
                    maximumAge: 300000
                });
            }
        };

        $scope.list = function () {
            if ($scope.query) {
                $scope.search();
            } else {
                $scope.getGeoLocation();
            }
        };

        $scope.list();
    }]);
