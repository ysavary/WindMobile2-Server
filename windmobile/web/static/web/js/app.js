var windmobileApp = angular.module('windmobile', ['ui.router', 'windmobile.controllers'],
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
                    controller: 'MapController as main'
                })
                .state('map.detail', {
                    url: '/:stationId',
                    views: {
                        "detailView": {
                            templateUrl: '/static/web/templates/detail.html',
                            controller: 'DetailController as detail'
                        }
                    }
                })
                .state('list', {
                    url: '/list',
                    templateUrl: '/static/web/templates/list.html',
                    controller: 'ListController as main'
                })
                .state('list.detail', {
                    url: '/:stationId',
                    views: {
                        "detailView": {
                            templateUrl: '/static/web/templates/detail.html',
                            controller: 'DetailController as detail'
                        }
                    }
                });
            $urlRouterProvider.otherwise("/map");
        }])
    .run(function ($rootScope) {
        $rootScope.$on('$stateChangeSuccess',
            function (event, toState, toParams, fromState, fromParams) {
                $rootScope.controller = toState.name.split('.')[0];
            });
    })
    .filter('fromNow', function () {
        return function (input) {
            if (input) {
                return moment.unix(input).fromNow();
            }
            return "Unknown";
        };
    })
    .directive('wdmWindMiniChart', function () {
        return {
            restrict: "C",
            link: function (scope, element, attrs) {
                scope.$watch(element.attr('data-scope-watch'), function (newValue, oldValue) {
                    if (newValue && newValue.data) {
                        var values = newValue.data;

                        var data = [];
                        var count = values.length;
                        for (var i = count - 1; i >= 0; i--) {
                            data.push([values[i]['_id'], values[i]['w-avg']]);
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
                                fillColor: '#444',
                                lineColor: '#ddd'
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
                var width = 100;
                var height = 100;
                var radius = Math.min(width, height) / 2;
                var fontSize = 9;


                var paper = Snap(element[0]);
                var circleRadius = radius - 1;
                var circle = paper.circle(width / 2, height / 2, circleRadius);
                circle.attr({
                    stroke: "#8D8D8D",
                    strokeWidth: 1
                });

                var labels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
                var labelRadius = radius - fontSize / 2 - 6;
                var angle = 0;
                for (var i = 0; i < labels.length; i++) {
                    var angleRadian = (angle + 90) * (Math.PI / 180);
                    var x = width / 2 - Math.cos(angleRadian) * labelRadius;
                    var y = height / 2 - Math.sin(angleRadian) * labelRadius;

                    var text = paper.text(x, y, labels[i]);
                    text = text.attr({
                        fill: "#8D8D8D",
                        'font-size': fontSize,
                        'alignment-baseline': 'inherit'

                    });
                    angle += 45;
                }


                scope.$watch(element.attr('data-scope-watch'), function (newValue, oldValue) {
                    if (newValue && newValue.data) {
                        element.find(".wdm-direction-line").remove();

                        var values = newValue.data;

                        // The center
                        var lastX = width / 2;
                        var lastY = width / 2;

                        var currentRadius = 0.0;
                        for (var i = values.length - 1; i >= 0; i--) {
                            var direction = values[i]['w-dir'];

                            currentRadius += circleRadius / values.length;
                            var directionRadian = (direction + 90) * (Math.PI / 180);

                            var x = width / 2 - Math.cos(directionRadian) * currentRadius;
                            var y = height / 2 - Math.sin(directionRadian) * currentRadius;

                            var line = paper.line(lastX, lastY, x, y);
                            line.attr({
                                class: 'wdm-direction-line',
                                stroke: '#bfbb3d',
                                strokeWidth: 1.5
                            });

                            lastX = x;
                            lastY = y;
                        }
                    }
                });
            }
        }
    })
    .directive('wdmWindChart', function () {
        return {
            restrict: "C",
            link: function (scope, element, attrs) {
                scope.$watch(element.attr('data-scope-watch'), function (value) {
                    if (value) {
                        var windAvgSerie = {
                            name: 'windAvg',
                            type: 'areaspline',
                            color: '#444',
                            lineWidth: 1,
                            lineColor: '#ddd',
                            marker: {
                                enabled: false
                            },
                            data: []
                        };
                        var windMaxSerie = {
                            name: 'windMax',
                            type: 'spline',
                            color: '#b6b23d',
                            lineWidth: 1,
                            marker: {
                                enabled: false
                            },
                            data: []
                        };
                        var count = value.length;
                        for (var i = count - 1; i >= 0; i--) {
                            var date = value[i]['_id'] * 1000;
                            var windMax = value[i]['w-max'];
                            var windAvg = value[i]['w-avg'];

                            windMaxSerie.data.push([date, windMax]);
                            windAvgSerie.data.push([date, windAvg]);
                        }
                        $(element).highcharts('StockChart', {
                            legend: {
                                enabled: false
                            },
                            chart: {
                                backgroundColor: null
                            },
                            plotOptions: {
                                series: {
                                    animation: false,
                                    states: {
                                        hover: {
                                            enabled: false
                                        }
                                    }
                                }
                            },
                            tooltip: {
                                enabled: false,
                                crosshairs: false
                            },
                            xAxis: {
                                type: 'datetime'
                            },
                            yAxis: {
                                gridLineWidth: 0.5,
                                gridLineColor: '#555'
                            },
                            series: [windAvgSerie, windMaxSerie],
                            navigator: {
                                enabled: false
                            },
                            scrollbar: {
                                enabled: false
                            },
                            rangeSelector: {
                                inputEnabled: false,
                                buttons: [{
                                    type: 'day',
                                    count: 2,
                                    text: '2 days'
                                }, {
                                    type: 'day',
                                    count: 1,
                                    text: '1 day'
                                }, {
                                    type: 'hour',
                                    count: 12,
                                    text: '12 hours'
                                }, {
                                    type: 'hour',
                                    count: 6,
                                    text: '6 hours'
                                }],
                                selected: 3,
                                buttonTheme: {
                                    width: 50,
                                    fill: 'none',
                                    stroke: 'none',
                                    'stroke-width': 0,
                                    r: 8,
                                    style: {
                                        color: '#8d8d8d'
                                    },
                                    states: {
                                        hover: {
                                            fill: 'none',
                                            style: {
                                                color: '#ddd'
                                            }
                                        },
                                        select: {
                                            fill: 'none',
                                            style: {
                                                color: '#ddd'
                                            }
                                        }
                                    }
                                }
                            }
                        });
                    }
                });
            }
        }
    })
    .directive('wdmAirChart', function () {
        return {
            restrict: "C",
            link: function (scope, element, attrs) {
                scope.$watch(element.attr('data-scope-watch'), function (value) {
                    if (value) {
                        var temperatureSerie = {
                            name: 'temperature',
                            type: 'spline',
                            color: '#c72d46',
                            lineWidth: 1,
                            marker: {
                                enabled: false
                            },
                            data: []
                        };
                        var humiditySerie = {
                            name: 'humidity',
                            type: 'spline',
                            color: '#3b71a0',
                            lineWidth: 1,
                            marker: {
                                enabled: false
                            },
                            yAxis: 1,
                            data: []
                        };
                        var rainSerie = {
                            name: 'rain',
                            type: 'column',
                            borderColor: '#444',
                            borderWidth: 0.5,
                            color: 'rgba(30, 30, 30, 0.4)',
                            marker: {
                                enabled: false
                            },
                            yAxis: 2,
                            data: []
                        };
                        var count = value.length;
                        for (var i = count - 1; i >= 0; i--) {
                            var date = value[i]['_id'] * 1000;
                            temperatureSerie.data.push([date, value[i]['temp']]);
                            humiditySerie.data.push([date, value[i]['hum']]);
                            rainSerie.data.push([date, value[i]['rain']]);
                        }
                        $(element).highcharts('StockChart', {
                            legend: {
                                enabled: false
                            },
                            chart: {
                                backgroundColor: null
                            },
                            plotOptions: {
                                series: {
                                    animation: false,
                                    states: {
                                        hover: {
                                            enabled: false
                                        }
                                    }
                                }
                            },
                            tooltip: {
                                enabled: false,
                                crosshairs: false
                            },
                            xAxis: {
                                type: 'datetime'
                            },
                            yAxis: [{
                                gridLineWidth: 0.5,
                                gridLineColor: "#555"
                            }, {
                                opposite: false,
                                gridLineWidth: 0,
                                labels: {
                                    enabled: false
                                }
                            }, {
                                gridLineWidth: 0,
                                labels: {
                                    enabled: false
                                }
                            }],
                            series: [rainSerie, temperatureSerie, humiditySerie],
                            navigator: {
                                enabled: false
                            },
                            scrollbar: {
                                enabled: false
                            },
                            rangeSelector: {
                                inputEnabled: false,
                                buttons: [{
                                    type: 'day',
                                    count: 2,
                                    text: '2 days'
                                }, {
                                    type: 'day',
                                    count: 1,
                                    text: '1 day'
                                }, {
                                    type: 'hour',
                                    count: 12,
                                    text: '12 hours'
                                }, {
                                    type: 'hour',
                                    count: 6,
                                    text: '6 hours'
                                }],
                                selected: 3,
                                buttonTheme: {
                                    width: 50,
                                    fill: 'none',
                                    stroke: 'none',
                                    'stroke-width': 0,
                                    r: 8,
                                    style: {
                                        color: '#8d8d8d'
                                    },
                                    states: {
                                        hover: {
                                            fill: 'none',
                                            style: {
                                                color: '#ddd'
                                            }
                                        },
                                        select: {
                                            fill: 'none',
                                            style: {
                                                color: '#ddd'
                                            }
                                        }
                                    }
                                }
                            }
                        });
                    }
                });
            }
        }
    });