var app = angular.module('windMobile', ['ui.router', 'windMobile.list', 'windMobile.map', 'windMobile.detail'],
    function ($interpolateProvider) {
        $interpolateProvider.startSymbol('[[');
        $interpolateProvider.endSymbol(']]');
    })
    .config(['$locationProvider', '$stateProvider', '$urlRouterProvider',
            function ($locationProvider, $stateProvider, $urlRouterProvider) {
        $locationProvider.html5Mode(true);
        $stateProvider
            .state('map', {
                url: '/map',
                templateUrl: '/static/web/templates/map.html',
                controller: 'MapController'
            })
            .state('list', {
                url: '/list',
                templateUrl: '/static/web/templates/list.html',
                controller: 'ListController'
            })
            .state('detail', {
                url: '/station/:stationId',
                templateUrl: '/static/web/templates/detail.html',
                controller: 'DetailController'
            });
        $urlRouterProvider.otherwise("/map");
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
                            chartRangeMin: 0,
                            disableInteraction: true,
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
            link: function (scope, element, attrs) {
                scope.$watch('historic', function (newValue, oldValue) {
                    var width = parseFloat($(element[0]).width());
                    var height = parseFloat($(element[0]).height());

                    if (width && height) {
                        var paper = Snap(element[0]);
                        var radius = Math.min(width, height) / 2;
                        var circle = paper.circle(width / 2, height / 2, radius - 1);
                        circle.attr({
                            stroke: "#fff",
                            strokeWidth: 1
                        });
                    }

                    if (newValue) {
                        // The center
                        var lastX = width / 2;
                        var lastY = width / 2;

                        var currentRadius = 0.0;
                        for (var i = newValue.length - 1; i >= 0; i--) {
                            var direction = newValue[i]['w-dir'];

                            currentRadius += radius / newValue.length;
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
                    }
                });
            }
        }
    });