var app = angular.module('windMobile', ['ngRoute', 'windMobile.list', 'windMobile.map', 'windMobile.detail'],
    function ($interpolateProvider) {
        $interpolateProvider.startSymbol('[[');
        $interpolateProvider.endSymbol(']]');
    })
    .config(['$routeProvider', function ($routeProvider) {
        $routeProvider.otherwise({redirectTo: '/list'});
    }])
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
                    scope.$watch('historic', function (newValue, oldValue) {
                        var width = parseFloat($(element[0]).width());
                        var height = parseFloat($(element[0]).height());

                        var radius = Math.min(width, height) / 2;

                        var paper = Snap(element[0]);
                        var circle = paper.circle(width / 2, height / 2, radius - 1);
                        circle.attr({
                            stroke: "#fff",
                            strokeWidth: 1
                        });

                        // The center
                        var lastX = width / 2;
                        var lastY = width / 2;

                        var currentRadius = 0.0;
                        for (var i = 0; i < scope.historic.length; i++) {
                            var direction = scope.historic[i]['w-dir'];

                            currentRadius += radius / scope.historic.length;
                            var directionRadian = (direction + 90) * (Math.PI / 180);

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