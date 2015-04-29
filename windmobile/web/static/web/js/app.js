var app = angular.module('windmobile', ['ui.router', 'windmobile.list', 'windmobile.map'],
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
        };
    })
    .directive('wdmWindMiniChart', function () {
        return {
            restrict: "C",
            link: function (scope, element, attrs) {
                scope.$watch('historic', function (newValue, oldValue) {
                    if (newValue) {
                        var data = [];
                        var count = newValue.length;
                        for (var i = count - 1; i >= 0; i--) {
                            data.push([newValue[i]['_id'], newValue[i]['w-avg']]);
                        }
                        if (data.length > 0) {
                            element.sparkline(data, {
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
                        }
                    }
                });
            }
        };
    })
    .directive('wdmWindDirection', function () {
        return {
            restrict: "C",
            link: function (scope, element, attrs) {
                scope.$watch('historic', function (newValue, oldValue) {
                    var width = parseFloat($(element[0]).width());
                    var height = parseFloat($(element[0]).height());

                    if (width && height) {
                        var paper = Snap(element[0]);
                        var radius = Math.min(width, height) / 2;
                        var circle = paper.circle(width / 2, height / 2, radius - 1);
                        circle.attr({
                            stroke: "#8D8D8D",
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
                                stroke: "#cccc00",
                                strokeWidth: 1.5
                            });

                            lastX = x;
                            lastY = y;
                        }
                    }
                });
            }
        }
    });
