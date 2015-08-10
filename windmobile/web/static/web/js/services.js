var angular = require('angular');
var moment = require('moment');
var tinycolor = require('tinycolor2');

angular.module('windmobile.services', [])
    .factory('utils', function () {
        return {
            fromNowInterval: 30000,
            refreshInterval: 120000,
            getStationStatus: function (station) {
                // status: 0=red, 1=orange, 2=green
                var stationValue;
                if (station.status === 'green') {
                    stationValue = 2;
                } else {
                    if (station.status === 'orange') {
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
            getStatusClass: function (status) {
                // status: 0=red, 1=orange, 2=green
                if (status === 0) {
                    return 'wdm-status-red';
                }
                if (status === 1) {
                    return 'wdm-status-orange';
                }
            },
            getColorInRange: function (value, max) {
                var hueStart = 90;

                var hue = hueStart + (value / max) * (360 - hueStart);
                if (hue > 360) {
                    hue = 360;
                }
                return tinycolor.fromRatio({h: hue, s: 1, v: 0.7}).toHexString();
            },
            getWindDirectionLabel: function (labels, direction) {
                var sectors = 360 / labels.length;
                var angle = 0;
                for (var i = 0; i < labels.length; i++) {
                    var min = angle - sectors / 2;
                    var max = angle + sectors / 2;

                    if (i == 0) {
                        // Looking for the north "half sector" from 337.5 to 360
                        if ((direction >= 360 + min) && (direction <= 360)) {
                            return labels[0];
                        }
                    }
                    if ((direction >= min) && (direction < max)) {
                        return labels[i];
                    }
                    angle += sectors;
                }
            }
        };
    });
