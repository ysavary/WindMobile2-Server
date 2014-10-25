angular.module('windMobile.map', ['ngRoute', 'ngMap'])

    .config(['$routeProvider', function ($routeProvider) {
        $routeProvider.when('/map', {
            templateUrl: '/static/web/js/map/map.html',
            controller: 'MapController'
        });
    }])

    .controller('MapController', ['$scope', '$http', '$compile', function ($scope, $http, $compile) {
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

            for (var i = 0; i < stations.length; i++) {
                var station = stations[i];

                var position = new google.maps.LatLng(station.loc.lat, station.loc.lon);
                var marker = new google.maps.Marker({
                    title: station["short"],
                    position: position,
                    map: $scope.map
                });
                marker.station = station;
                markersArray.push(marker);

                //var element = $compile('<div class="station-card" ng-include src="\'/static/web/templates/_infobox.html\'" ng-controller="StationController"></div>')($scope);
                var content = '<div class="station-card transparent-background">' +
                    '<div class="title">[[ station.name ]]</div>' +
                    '<div class="last-update">[[ station.last._id|fromNow ]]</div>' +
                    '<div class="altitude">[[ station.alt ]] meters</div>' +
                    '<div class="wind-section">' +
                    '<div class="wind-avg">[[ station.last[\'w-avg\'].toFixed(1) ]]</div>' +
                    '<div class="wind-max">[[ station.last[\'w-max\'].toFixed(1) ]]</div>' +
                    '<div class="unit">km/h</div>' +
                    //'<mini-chart id="mini-chart" data="[[ miniChartData ]]"></mini-chart>' +
                    '</div>' +
                    '<svg id="wind-direction" obj="" wind-direction></svg>' +
                    '</div>';

                /*
                 $scope.station = null;
                 $scope.historic = [];
                 var element = $compile(content)($scope);
                 */

                google.maps.event.addListener(marker, 'click', function () {
                    if (infoBox) {
                        infoBox.close();
                    }
                    $scope.station = this.station;
                    $scope.historic = [];
                    $scope.getHistoric();
                    var element = $compile(content)($scope);
                    $scope.$apply();
                    infoBox = new InfoBox({
                        content: element[0]
                    });
                    infoBox.open($scope.map, this);
                });
            }
        }

        $scope.getHistoric = function () {
            $scope.historic = [];
            $http({method: 'GET', url: '/api/2/stations/' + $scope.station._id + '/historic?duration=3600'}).
                success(function (data) {
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
