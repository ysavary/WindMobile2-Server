angular.module('windmobile.services', [])
    .factory('utils', function () {
        return {
            getStationStatus: function (station) {
                var result = 'green';
                if (station.status != 'green') {
                    if (station.status == 'orange') {
                        result = 'orange';
                    } else {
                        result = 'red';
                    }
                } else if (station.last) {
                    if (moment.unix(station.last._id).isBefore(moment().subtract(2, 'hours'))) {
                        result = 'red';
                    } else if (moment.unix(station.last._id).isBefore(moment().subtract(1, 'hours'))) {
                        result = 'orange';
                    }
                } else {
                    result = 'red';
                }
                return result;
            },
            getStatusColor: function (status) {
                if (status == 'red') {
                    return {color: '#900'};
                } else if (status == 'orange') {
                    return {color: '#8a5f0f'};
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
