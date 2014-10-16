angular.module('windMobile.detail', ['ngRoute'])

    .config(['$routeProvider', function ($routeProvider) {
        $routeProvider.when('/station/:stationId', {
            templateUrl: '/static/web/js/detail/detail.html',
            controller: 'DetailController'
        });
    }])

    .controller('DetailController', ['$scope', '$http', '$routeParams', function ($scope, $http, $routeParams) {
        $scope.stationId = $routeParams.stationId;

        $scope.getData = function () {
            $scope.station = null;
            $http({method: 'GET', url: '/api/2/stations/' + $scope.stationId}).
                success(function (data) {
                    $scope.station = data;
                })
        };

        $scope.getHistoric = function () {
            $scope.historic = [];
            $http({method: 'GET', url: '/api/2/stations/' + $scope.stationId + '/historic?duration=3600'}).
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

        $scope.windChart = function () {
            $http({method: 'GET', url: '/api/2/stations/' + $scope.stationId + '/historic?duration=172800'}).
                success(function (data) {
                    var windAvgSerie = {
                        name: 'windAvg',
                        type: 'areaspline',
                        color: {
                            linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
                            stops: [
                                [0, '#a7a9cb'],
                                [1, '#252ccb']
                            ]
                        },
                        lineWidth: 1,
                        lineColor: '#ffffff',
                        marker: {
                            enabled: false
                        },
                        data: []
                    };
                    var windMaxSerie = {
                        name: 'windMax',
                        type: 'spline',
                        color: '#e32d2d',
                        lineWidth: 1,
                        marker: {
                            enabled: false
                        },
                        data: []
                    };
                    var count = data.length;
                    for (var i = count - 1; i >= 0; i--) {
                        var date = data[i]['_id'] * 1000;
                        windMaxSerie.data.push([date, data[i]['w-max']]);
                        windAvgSerie.data.push([date, data[i]['w-avg']]);
                    }
                    $('#wind-chart').highcharts('StockChart', {
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
                            enabled: false
                        },
                        xAxis: {
                            type: 'datetime'
                        },
                        yAxis: {
                            gridLineWidth: 0.5,
                            title: {
                                text: 'km/h'
                            }
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
                            selected:3,
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
                                        fill: 'none'
                                    },
                                    select: {
                                        fill: 'none',
                                        style: {
                                            color: '#ddd',
                                            fontWeight: 'bold'
                                        }
                                    }
                                }
                            }
                        }
                    });
                });
        };

        $scope.getData();
        $scope.getHistoric();
        $scope.windChart();
    }]);
