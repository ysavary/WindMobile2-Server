angular.module('windMobile.list', ['ngRoute'])

    .config(['$routeProvider', function ($routeProvider) {
        $routeProvider.when('/list', {
            templateUrl: '/static/web/js/list/list.html',
            controller: 'ListController'
        });
    }])

    .controller('ListController', ['$scope', '$http', '$location', function ($scope, $http, $location) {
        $scope.snapOptions = {
            disable: 'right'
        };
        $scope.geoSearch = function (position) {
            var params = {};
            params.lat = position.coords.latitude;
            params.lon = position.coords.longitude;
            $http({method: 'GET', url: '/api/2/stations/', params: params}).
                success(function (data) {
                    $scope.stations = data;
                })
        };
        $scope.search = function () {
            var params = {};
            params.search = $scope.query;
            $http({method: 'GET', url: '/api/2/stations/', params: params}).
                success(function (data) {
                    $scope.stations = data;
                })
        };
        $scope.getGeoLocation = function () {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition($scope.geoSearch, $scope.search);
            }
        };
        $scope.list = function () {
            if ($scope.query) {
                $scope.search();
            } else {
                $scope.getGeoLocation();
            }
        };
        $scope.selectStation = function (station) {
            $location.path('/station/' + station._id);
        };
        $scope.list();
    }])

    .controller('StationController', ['$scope', '$http', function ($scope, $http) {
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

