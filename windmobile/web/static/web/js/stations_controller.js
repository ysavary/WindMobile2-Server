var module = angular.module('WindMobileModule', [], function ($interpolateProvider) {
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
    });

module.directive('minichart', function () {
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
                        type: 'line',
                        spotColor: false,
                        minSpotColor: false,
                        maxSpotColor: false
                    });
                });
            };
        }
    };
});

function StationsController($scope, $http) {
    $scope.list = function () {
        var params = {};
        params.search = $scope.query;
        $http({method: 'GET', url: '/api/2/stations/', params: params}).
            success(function (data) {
                $scope.stations = data;
            })
    }
    $scope.list();
}

function StationController($scope, $http) {
    $scope.getHistoric = function () {
        $http({method: 'GET', url: '/api/2/stations/' + $scope.station._id + '/historic/'}).
            success(function (data) {
                var chart = '';
                var count = data.length;
                for (var i = count - 1; i >= 0; i--) {
                    chart += data[i]['_id'] + ':' + data[i]['w-avg'];
                    if (i > 0) {
                        chart += ',';
                    }
                }
                $scope.historic = chart;

            })
    }
    $scope.getHistoric()
}