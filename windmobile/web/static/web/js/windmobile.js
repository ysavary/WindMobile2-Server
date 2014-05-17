var app = angular.module('WindMobileApp', ['snap', 'google-maps'], function ($interpolateProvider) {
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
    .directive('miniChart', function () {
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
                            width: '80px',
                            height: '25px',
                            type: 'line',
                            spotColor: false,
                            minSpotColor: false,
                            maxSpotColor: false,
                            lineColor: '#fff',
                            fillColor: '#444'
                        });
                    });
                };
            }
        };
    })
    .directive('windDirection', function () {
        return {
            restrict: "A",
            compile: function (tElement, tAttrs, transclude) {
                return function (scope, element, attrs) {
                    scope.$watch('historic', function(newValue, oldValue) {
                        var width = parseFloat($(element[0]).width());
                        var height = parseFloat($(element[0]).height());

                        var radius = Math.min(width, height) / 2;

                        var paper = Snap(element[0]);
                        var circle = paper.circle(width/2, height/2, radius-1);
                        circle.attr({
                            stroke: "#fff",
                            strokeWidth: 1
                        });

                        // The center
                        var lastX = width/2;
                        var lastY = width/2;

                        var currentRadius = 0.0;
                        for (var i = 0; i < scope.historic.length; i++) {
                            var direction = scope.historic[i]['w-dir'];

                            currentRadius += radius / scope.historic.length;
                            var directionRadian = (direction + 90) * (Math.PI/180);

                            var x = radius - Math.cos(directionRadian) * currentRadius;
                            var y = radius - Math.sin(directionRadian) * currentRadius;

                            var line = paper.line(lastX, lastY, x, y);
                            line.attr({
                                stroke: "#f00",
                                strokeWidth: 2
                            });

                            lastX = x;
                            lastY = y;
                        }
                    });
                }
            }
        }
    });

app.controller('StationsController', ['$scope', '$http', function($scope, $http) {
    $scope.snapOptions = {
        disable: 'right'
    };
    $scope.list = function () {
        var params = {};
        params.search = $scope.query;
        $http({method: 'GET', url: '/api/2/stations/', params: params}).
            success(function (data) {
                $scope.stations = data;
            })
    }
    $scope.list();
}]);

app.controller('StationController', ['$scope', '$http', function($scope, $http) {
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
    $scope.getHistoric();
}]);

app.controller('MapController', ['$scope', '$http', function($scope, $http) {
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
}]);