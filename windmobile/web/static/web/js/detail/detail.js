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

        $scope.getData();
        $scope.getHistoric();
    }]);
