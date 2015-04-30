angular.module('windmobile.map', ['windmobile.services'])

    .controller('MapController', ['$scope', '$http', '$compile', '$templateCache', '$location', 'utils',
        function ($scope, $http, $compile, $templateCache, $location, utils) {
            var markersArray = [];
            var inboBoxContent = $compile($templateCache.get('_infobox.html'))($scope);

            var mapOptions = {
                // France and Switzerland
                center: new google.maps.LatLng(46.76, 4.08),
                zoom: 6,
                panControl: false,
                mapTypeControlOptions: {
                    mapTypeIds: [google.maps.MapTypeId.TERRAIN, google.maps.MapTypeId.ROADMAP,
                        google.maps.MapTypeId.SATELLITE]
                },
                mapTypeId: google.maps.MapTypeId.TERRAIN
            };
            $scope.map = new google.maps.Map(document.getElementById('map'), mapOptions);

            function clearOverlays() {
                if ($scope.infoBox) {
                    $scope.infoBox.close();
                }
                for (var i = 0; i < markersArray.length; i++) {
                    markersArray[i].setMap(null);
                }
                markersArray.length = 0;
            }

            function displayMarkers(stations) {
                clearOverlays();

                for (var i = 0; i < stations.length; i++) {
                    var station = stations[i];
                    var status = utils.getStationStatus(station);

                    var color;
                    if (status == 0) {
                        color = '#808080';
                    } else {
                        color = utils.getColorInRange(station.last['w-max'], 50);
                    }

                    var icon = {
                        path: 'M21,149.2v86.3L-19,213l50,77l50-77l-40,22.5v-86.3c28.4-4.8,50-29.4,50-59.2S69.4,35.6,41,30.8V-83H21V30.8C-7.4,35.6-29,60.3-29,90S-7.4,144.4,21,149.2z M31,50c22.1,0,40,17.9,40,40s-17.9,40-40,40S-9,112.1-9,90S8.9,50,31,50z',
                        scale: 0.15,
                        fillOpacity: 1,
                        fillColor: color,
                        strokeColor: color,
                        strokeWeight: 2,
                        rotation: (station.last ? station.last['w-dir'] : 0)
                    };

                    var marker = new google.maps.Marker({
                        title: station["short"],
                        position: new google.maps.LatLng(station.loc.coordinates[1], station.loc.coordinates[0]),
                        icon: icon,
                        map: $scope.map
                    });
                    marker.station = station;
                    markersArray.push(marker);

                    (function (marker) {
                        google.maps.event.addListener(marker, 'click', function () {
                            if ($scope.infoBox) {
                                $scope.infoBox.close();
                            }
                            $scope.station = marker.station;
                            $scope.getHistoric();
                            $scope.infoBox = new InfoBox({
                                content: inboBoxContent[0],
                                closeBoxURL: ''
                            });
                            $scope.infoBox.open($scope.map, marker);
                        })
                    })(marker);

                    google.maps.event.addListener($scope.map, 'click', function () {
                        if ($scope.infoBox) {
                            $scope.infoBox.close();
                        }
                    });
                }
            }

            $scope.getHistoric = function () {
                $http({method: 'GET', url: '/api/2/stations/' + $scope.station._id + '/historic?duration=3600'})
                    .success(function (data) {
                        var historic = {};
                        historic.data = data;
                        var windAvg = function(value) {
                            return value['w-avg'];
                        };
                        historic['w-avg'] = {};
                        historic['w-avg'].min = Math.min.apply(null, data.map(windAvg));
                        historic['w-avg'].mean = data.map(windAvg).reduce(function (previousValue, currentValue) {
                                return previousValue + currentValue;
                            }, 0) / data.length;
                        historic['w-avg'].max = Math.max.apply(null, data.map(windAvg));
                        $scope.historic = historic;
                    })
            };
            $scope.geoSearch = function (position) {
                var currentPosition = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
                $scope.map.setCenter(currentPosition);
                $scope.map.setZoom(8);

                var params = {};
                params.lat = position.coords.latitude;
                params.lon = position.coords.longitude;
                params.limit = 1000;

                $http({method: 'GET', url: '/api/2/stations/', params: params}).success(displayMarkers);
            };
            $scope.search = function () {
                var params = {};
                params.search = $scope.query;
                params.limit = 1000;
                $http({method: 'GET', url: '/api/2/stations/', params: params}).success(displayMarkers);
            };
            $scope.getGeoLocation = function () {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition($scope.geoSearch, $scope.search, {
                        enableHighAccuracy: true,
                        timeout: 3000,
                        maximumAge: 300000
                    });
                }
            };
            $scope.selectStation = function (station) {
                if ($scope.infoBox) {
                    $scope.infoBox.close();
                }
                $('#detailModal').modal();
                $('a[data-target="#tab2"]').on('shown.bs.tab', function (event) {
                    $scope.windChart();
                });
                $('a[data-target="#tab3"]').on('shown.bs.tab', function (event) {
                    $scope.airChart();
                });
            };
            $scope.setColorStatus = function (station) {
                if (station) {
                    var status = utils.getStationStatus(station);
                    return utils.getStatusColor(status);
                }
            };
            $scope.list = function () {
                if ($scope.query) {
                    $scope.search();
                } else {
                    $scope.getGeoLocation();
                }
            };
            $scope.windChart = function () {
                $http({method: 'GET', url: '/api/2/stations/' + $scope.station._id + '/historic?duration=172800'})
                    .success(function (data) {
                        // Wind
                        var windAvgSerie = {
                            name: 'windAvg',
                            type: 'areaspline',
                            color: '#444444',
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
                        var windMaxMax = 0;
                        var count = data.length;
                        for (var i = count - 1; i >= 0; i--) {
                            var date = data[i]['_id'] * 1000;
                            var windMax = data[i]['w-max'];
                            var windAvg = data[i]['w-avg'];

                            windMaxMax = Math.max(windMaxMax, windMax);

                            windMaxSerie.data.push([date, windMax]);
                            windAvgSerie.data.push([date, windAvg]);
                        }
                        $('.wdm-wind-chart').highcharts('StockChart', {
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
                                title: {
                                    text: 'km/h'
                                },
                                max: windMaxMax
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
                    });
            };
            $scope.airChart = function () {
                $http({method: 'GET', url: '/api/2/stations/' + $scope.station._id + '/historic?duration=172800'})
                    .success(function (data) {
                        // Air
                        var temperatureSerie = {
                            name: 'temperature',
                            type: 'spline',
                            color: '#a7a9cb',
                            lineWidth: 1,
                            marker: {
                                enabled: false
                            },
                            data: []
                        };
                        var humiditySerie = {
                            name: 'humidity',
                            type: 'spline',
                            color: '#a7a9cb',
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
                            color: '#a7a9cb',
                            lineWidth: 1,
                            marker: {
                                enabled: false
                            },
                            yAxis: 2,
                            data: []
                        };
                        var count = data.length;
                        for (var i = count - 1; i >= 0; i--) {
                            var date = data[i]['_id'] * 1000;
                            temperatureSerie.data.push([date, data[i]['temp']]);
                            humiditySerie.data.push([date, data[i]['hum']]);
                            rainSerie.data.push([date, data[i]['rain']]);
                        }
                        $('.wdm-temp-chart').highcharts('StockChart', {
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
                                title: {
                                    text: '°C'
                                }
                            }, {
                                gridLineWidth: 0.5,
                                title: {
                                    text: 'humidity'
                                },
                                opposite: false
                            }, {
                                gridLineWidth: 0.5,
                                    title: {
                                    text: 'rain'
                                }
                            }],
                            series: [temperatureSerie, humiditySerie, rainSerie],
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
                    });
            };
            $scope.list();
        }]);
