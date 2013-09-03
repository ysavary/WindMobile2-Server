var module = angular.module('WindMobileModule', ['google-maps'], function ($interpolateProvider) {
        $interpolateProvider.startSymbol('[[');
        $interpolateProvider.endSymbol(']]');
    })
    .filter('fromNow', function () {
        return function (input) {
            if (input) {
                return moment.unix(input).fromNow();
            } else {
                return "Unknown";
            }
        }
    })
    .directive('minichart', function () {
        return {
            restrict: "E",
            scope: {
                data: "@"
            },
            compile: function (tElement, tAttrs, transclude) {
                return function (scope, element, attrs) {
                    attrs.$observe('data', function (newValue) {
                        element.html(newValue);
                        element.sparkline('html', {
                            type: 'line',
                            spotColor: false,
                            minSpotColor: false,
                            maxSpotColor: false,
                            width: '40px'
                        });
                    });
                };
            }
        };
    });

function StationsController($scope, $http) {
    $scope.list = function () {
        var params = {};
        params.search = $scope.query;
        $http({method: 'GET', url: '/api/2/stations/', params: params}).
            success(function (data) {
                $scope.stations = data;
            })
    }
    $scope.list();
}

function StationController($scope, $http) {
    $scope.getHistoric = function () {
        $http({method: 'GET', url: '/api/2/stations/' + $scope.station._id + '/historic/'}).
            success(function (data) {
                var chart = '';
                var count = data.length;
                for (var i = count - 1; i >= 0; i--) {
                    chart += data[i]['_id'] + ':' + data[i]['w-avg'];
                    if (i > 0) {
                        chart += ',';
                    }
                }
                $scope.historic = chart;

            })
    }
    $scope.getHistoric()
}

function MapController($scope, $http) {
    $scope.center = {
            latitude: 0,
            longitude: 0
    };
    $scope.zoom= 5;
    $scope.markers = [];

    $scope.list = function () {
        $http({method: 'GET', url: '/api/2/stations/', params: {limit: 1000}}).
            success(function (stations) {
                for (var i = 0; i < stations.length; i++) {
                    $scope.markers.push({
                        latitude: stations[i].loc.lat,
                        longitude: stations[i].loc.lon
                    });
                }
            });
    }
    $scope.list();
}