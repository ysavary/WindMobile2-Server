angular.module('windmobile.services', [])
    .factory('utils', function () {
        return {
            getStationStatus: function (station) {
                // status: 0=red, 1=orange, 2=green
                var stationValue;
                if (station.status == 'green') {
                    stationValue = 2;
                } else {
                    if (station.status == 'orange') {
                        stationValue = 1;
                    } else {
                        stationValue = 0;
                    }
                }

                var lastValue;
                if (station.last) {
                    if (moment.unix(station.last._id).isBefore(moment().subtract(2, 'hours'))) {
                        lastValue = 0;
                    } else if (moment.unix(station.last._id).isBefore(moment().subtract(1, 'hours'))) {
                        lastValue = 1;
                    } else {
                        lastValue = 2;
                    }
                } else {
                    lastValue = 0;
                }
                return Math.min(stationValue, lastValue);
            },
            getStatusColor: function (status) {
                // status: 0=red, 1=orange, 2=green
                if (status == 0) {
                    return {color: '#990000'};
                } else if (status == 1) {
                    return {color: '#aa7109'};
                }
            },
            getColorInRange: function (value, max) {
                var hueStart = 90;

                var hue = hueStart + (value / max) * (360 - hueStart);
                if (hue > 360) {
                    hue = 360;
                }
                return tinycolor.fromRatio({ h: hue, s: 1, v: 0.7 }).toHexString();
            }
        }
    });
