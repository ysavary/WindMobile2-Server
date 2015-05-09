angular.module('windmobile.list', ['windmobile.services'])

    .controller('ListController', ['$http', function ($http) {
        var self = this;

        function geoSearch(position) {
            var params = {};
            params.lat = position.coords.latitude;
            params.lon = position.coords.longitude;
            $http({method: 'GET', url: '/api/2/stations/', params: params}).
                success(function (data) {
                    self.stations = data;
                });
        }
        function search() {
            var params = {};
            params.search = self.query;
            $http({method: 'GET', url: '/api/2/stations/', params: params}).
                success(function (data) {
                    self.stations = data;
                });
        }
        function getGeoLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(geoSearch, search, {
                    enableHighAccuracy: true,
                    timeout: 3000,
                    maximumAge: 300000
                });
            }
        }

        this.selectStation = function (station, historic) {
            this.selectedStation = station;
            this.selectedStation.historic = historic;
            $('#detailModal').modal();
            $('a[data-target="#tab2"]').on('shown.bs.tab', function (event) {
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + self.selectedStation._id + '/historic?duration=172800'
                }).success(function (data) {
                    self.selectedStation.windChart = data;
                });
            });
            $('a[data-target="#tab3"]').on('shown.bs.tab', function (event) {
                $http({
                    method: 'GET',
                    url: '/api/2/stations/' + self.selectedStation._id + '/historic?duration=172800'
                }).success(function (data) {
                    self.selectedStation.airChart = data;
                });
            });
        };
        this.list = function () {
            if (this.query) {
                search();
            } else {
                getGeoLocation();
            }
        };
        this.list();
    }])

    .controller('StationController', ['$scope', '$http', 'utils', function ($scope, $http, utils) {
        var self = this;

        this.setColorStatus = function (station) {
            var status = utils.getStationStatus(station);
            return utils.getStatusColor(status);
        };
        this.getHistoric = function () {
            $http({method: 'GET', url: '/api/2/stations/' + $scope.item._id + '/historic?duration=3600'}).
                success(function (data) {
                    var historic = {};
                    historic.data = data;
                    self.historic = historic;
                })
        };
        this.getHistoric();
    }]);
