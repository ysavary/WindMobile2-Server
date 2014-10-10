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
                        lineWidth: 2,
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
                        lineWidth: 2,
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
                    $('#chart').highcharts({
                        title: {
                            text: 'Wind speed'
                        },
                        legend: {
                            enabled: false
                        },
                        chart: {
                            backgroundColor: null
                        },
                        plotOptions: {
                            series: {
                                animation: false
                            }
                        },
                        xAxis: {
                            type: 'datetime'
                        },
                        yAxis: {
                            title: {
                                text: 'km/h'
                            }
                        },
                        series: [windAvgSerie, windMaxSerie]
                    });
                });
        };

        $scope.getData();
        $scope.getHistoric();
        $scope.windChart();
    }]);
