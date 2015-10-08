require('bootstrap-sass/assets/javascripts/bootstrap/modal.js');
require('bootstrap-sass/assets/javascripts/bootstrap/tab.js');

var angular = require('angular');
var Snap = require('snapsvg');
var moment = require('moment');
require('moment/locale/fr.js');
require('moment/locale/de.js');

angular.module('windmobile', [require('angular-ui-router'), require('angular-translate'), require('oclazyload'),
    'windmobile.services', 'windmobile.controllers'])
    .config(['$ocLazyLoadProvider', '$translateProvider', '$locationProvider', '$stateProvider', '$urlRouterProvider',
        function ($ocLazyLoadProvider, $translateProvider, $locationProvider, $stateProvider, $urlRouterProvider) {
            $ocLazyLoadProvider.config({
                events: true
            });

            $translateProvider
                .useSanitizeValueStrategy('escape')
                .translations('en', require('../locale/en.js'))
                .translations('fr', require('../locale/fr.js'))
                .registerAvailableLanguageKeys(['en', 'fr'], {
                    'en_*': 'en',
                    'fr_*': 'fr'
                })
                .fallbackLanguage('en')
                .determinePreferredLanguage();
            moment.locale($translateProvider.preferredLanguage());

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
                    },
                    resolve: {
                        loadMyCtrl: ['$ocLazyLoad', function ($ocLazyLoad) {
                            return $ocLazyLoad.load('/static/web/lib/highstock.js');
                        }]
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
                    },
                    resolve: {
                        loadMyCtrl: ['$ocLazyLoad', function ($ocLazyLoad) {
                            return $ocLazyLoad.load('/static/web/lib/highstock.js');
                        }]
                    }
                });
            $urlRouterProvider.otherwise("/map");
        }])
    .run(['$rootScope', '$location', '$window', function ($rootScope, $location, $window) {
        $rootScope.$on('ocLazyLoad.fileLoaded', function (event, file) {
            Highcharts.setOptions({
                global: {
                    useUTC: false
                },
                chart: {
                    backgroundColor: null,
                    resetZoomButton: {
                        theme: {
                            fill: 'none',
                            stroke: '#ddd',
                            style: {color: '#8d8d8d'}
                        }
                    }
                },
                legend: {
                    enabled: false
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
                rangeSelector: {
                    inputEnabled: false,
                    buttons: [
                        {type: 'day', count: 5, text: '5d'},
                        {type: 'day', count: 2, text: '2d'},
                        {type: 'day', count: 1, text: '1d'},
                        {type: 'hour', count: 12, text: '12h'},
                        {type: 'hour', count: 6, text: '6h'}
                    ],
                    selected: 4,
                    buttonTheme: {
                        width: 35,
                        fill: 'none',
                        stroke: 'none',
                        'stroke-width': 0,
                        r: 8,
                        style: {color: '#8d8d8d'},
                        states: {
                            hover: {
                                fill: 'none',
                                style: {color: '#ddd'}
                            },
                            select: {
                                fill: 'none',
                                style: {color: '#ddd'}
                            },
                            disabled: {
                                style: {color: '#666'}
                            }
                        }
                    }
                },
                loading: {
                    labelStyle: {color: 'white'},
                    style: {backgroundColor: 'transparent'}
                }
            });
        });
        $rootScope.$on('$stateChangeSuccess',
            function (event, toState, toParams, fromState, fromParams) {
                if ($window.ga) {
                    $window.ga('send', 'pageview', {page: $location.path()});
                }
                $rootScope.controller = toState.name.split('.')[0];
            });
    }])
    .directive('wdmWindMiniChart', function () {
        return {
            restrict: "C",
            link: function (scope, element, attrs) {
                var width = 100;
                var height = 40;
                var paper = Snap(element[0]);

                scope.$watch(element.attr('data-scope-watch'), function (newValue, oldValue) {
                    element.find(".wdm-minichart").remove();
                    if (newValue && newValue.data) {
                        var values = newValue.data;

                        var windKeys = [],
                            windValues = [];
                        for (var i = values.length - 1; i >= 0; i--) {
                            windKeys.push(values[i]['_id']);
                            windValues.push(values[i]['w-avg']);
                        }
                        var minX = Math.min.apply(null, windKeys),
                            maxX = Math.max.apply(null, windKeys),
                            minY = Math.min.apply(null, windValues),
                            maxY = Math.max.apply(null, windValues);
                        if (!minX || !maxX || (minY <= 0 && maxY <= 0)) {
                            return;
                        }
                        var scaleX = width / (maxX - minX);
                        var offsetY;
                        if (minY === 0) {
                            offsetY = 0;
                        } else {
                            offsetY = 5;
                        }
                        var scaleY = (height - offsetY) / (maxY - minY);

                        var points = [0, height];
                        for (var i = 0; i < windKeys.length - 1; i++) {
                            var x1 = (windKeys[i] - minX) * scaleX,
                                y1 = height - offsetY - (windValues[i] - minY) * scaleY,
                                x2 = (windKeys[i + 1] - minX) * scaleX,
                                y2 = height - offsetY - (windValues[i + 1] - minY) * scaleY;

                            points.push(x1, y1, x2, y2);
                        }
                        points.push(width, height);

                        var polygon = paper.polygon(points);
                        polygon.attr({
                            class: 'wdm-minichart',
                            fill: '#333'
                        });

                        // Remove first and last point
                        points.splice(0, 2);
                        points.splice(-2, 2);

                        var polyline = paper.polyline(points);
                        polyline.attr({
                            class: 'wdm-minichart wdm-minichart-line',
                            fill: 'none'
                        });
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
                    element.find(".wdm-direction").remove();
                    if (newValue && newValue.data) {
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
                                class: 'wdm-direction wdm-direction-line'
                            });

                            lastX = x;
                            lastY = y;
                        }
                    }
                });
            }
        }
    })
    .directive('wdmWindChart', ['utils', function (utils) {
        return {
            restrict: "C",
            link: function (scope, element, attrs) {
                var windAvgSerie = {
                    name: 'windAvg',
                    type: 'areaspline',
                    lineWidth: 1,
                    lineColor: '#676700',
                    color: '#333',
                    marker: {
                        enabled: false
                    }
                };
                var windDir = {};
                var windMaxSerie = {
                    name: 'windMax',
                    type: 'spline',
                    color: '#676700',
                    lineWidth: 1,
                    marker: {
                        enabled: false
                    },
                    dataLabels: {
                        enabled: true,
                        formatter: function () {
                            return utils.getWindDirectionLabel(
                                ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
                                windDir[this.key]
                            );
                        },
                        color: '#666',
                        style: {textShadow: false}
                    }
                };
                $(element).highcharts('StockChart', {
                    tooltip: {
                        enabled: false,
                        crosshairs: false
                    },
                    navigator: {
                        enabled: false
                    },
                    scrollbar: {
                        enabled: false
                    },
                    xAxis: {
                        type: 'datetime',
                        lineColor: '#8d8d8d'
                    },
                    yAxis: {
                        opposite: false,
                        gridLineWidth: 0.5,
                        gridLineColor: '#555',
                        labels: {
                            format: '{value} km/h',
                            style: {color: "#7d7d00", fontSize: '8.5px'}
                        }
                    },
                    series: [windAvgSerie, windMaxSerie]
                });
                element.highcharts().showLoading();

                scope.$watch(element.attr('data-scope-watch'), function (value) {
                    if (value) {
                        var chart = element.highcharts();
                        chart.hideLoading();
                        var serie0 = [], serie1 = [];
                        for (var i = value.length - 1; i >= 0; i--) {
                            var date = value[i]['_id'] * 1000;

                            serie0.push([date, value[i]['w-avg']]);
                            serie1.push([date, value[i]['w-max']]);
                            windDir[date] = value[i]['w-dir'];
                        }
                        chart.series[0].setData(serie0, false);
                        chart.series[1].setData(serie1, false);
                        // Workaround for https://github.com/highslide-software/highcharts.com/issues/4452
                        chart.xAxis[0].isDirtyExtremes = true;
                        chart.redraw(false);
                    }
                });
            }
        }
    }])
    .directive('wdmAirChart', function () {
        return {
            restrict: "C",
            link: function (scope, element, attrs) {
                var rainSerie = {
                    name: 'rain',
                    type: 'column',
                    borderColor: '#444',
                    borderWidth: 0.5,
                    color: 'rgba(30, 30, 30, 0.4)',
                    marker: {
                        enabled: false
                    },
                    yAxis: 2
                };
                var temperatureSerie = {
                    name: 'temperature',
                    type: 'spline',
                    color: '#891f30',
                    lineWidth: 1,
                    marker: {
                        enabled: false
                    }
                };
                var humiditySerie = {
                    name: 'humidity',
                    type: 'spline',
                    color: '#264a68',
                    lineWidth: 1,
                    marker: {
                        enabled: false
                    },
                    yAxis: 1
                };
                $(element).highcharts('StockChart', {
                    tooltip: {
                        enabled: false,
                        crosshairs: false
                    },
                    navigator: {
                        enabled: false
                    },
                    scrollbar: {
                        enabled: false
                    },
                    xAxis: {
                        type: 'datetime',
                        lineColor: '#8d8d8d'
                    },
                    yAxis: [{
                        opposite: false,
                        gridLineWidth: 0.5,
                        gridLineColor: "#555",
                        labels: {
                            format: '{value} °C',
                            style: {color: "#c72d46", fontSize: '8.5px'}
                        }
                    }, {
                        gridLineWidth: 0,
                        labels: {
                            format: '{value} %',
                            style: {color: "#3b71a0", fontSize: '8.5px'}
                        }
                    }, {
                        gridLineWidth: 0,
                        labels: {
                            enabled: false
                        }
                    }],
                    series: [rainSerie, temperatureSerie, humiditySerie]
                });
                element.highcharts().showLoading();

                scope.$watch(element.attr('data-scope-watch'), function (value) {
                    if (value) {
                        var chart = element.highcharts();
                        chart.hideLoading();
                        var serie0 = [], serie1 = [], serie2 = [];
                        for (var i = value.length - 1; i >= 0; i--) {
                            var date = value[i]['_id'] * 1000;

                            serie0.push([date, value[i]['rain']]);
                            serie1.push([date, value[i]['temp']]);
                            serie2.push([date, value[i]['hum']]);
                        }
                        chart.series[0].setData(serie0, false);
                        chart.series[1].setData(serie1, false);
                        chart.series[2].setData(serie2, false);
                        // Workaround for https://github.com/highslide-software/highcharts.com/issues/4452
                        chart.xAxis[0].isDirtyExtremes = true;
                        chart.redraw(false);
                    }
                });
            }
        }
    });