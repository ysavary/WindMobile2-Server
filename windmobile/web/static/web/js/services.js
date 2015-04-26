angular.module('windmobile.services', [])
    .factory('utils', function () {
        return {
            setColorStatus: function (station) {
                if (station && station.last) {
                    var color;
                    if (moment.unix(station.last._id).isBefore(moment().subtract(2, 'hours'))) {
                        color = '#900';
                    } else if (moment.unix(station.last._id).isBefore(moment().subtract(1, 'hours'))) {
                        color = '#8a5f0f';
                    }
                    return {color: color};
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
