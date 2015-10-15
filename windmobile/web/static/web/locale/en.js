(function () {
    en = {
        "Center": "Center",
        "List": "List",
        "Map": "Map",
        "Help": "Help",
        "Wind": "Wind",
        "Temperature": "Temperature",
        "Humidity": "Humidity",
        "Pressure": "Pressure",
        "Rain": "Rain",
        "Summary": "Summary",
        "last hour": "last hour",
        "Minimum": "Minimum",
        "Mean": "Mean",
        "Maximum": "Maximum",
        "Summit": "Summit",
        "Plain": "Plain",
        "no recent data": "no recent data",
        "meters": "meters",
        "Unable to find your location": "Unable to find your location"
    };

    // Node: Export function
    if (typeof module !== "undefined" && module.exports) {
        module.exports = en;
    }
    // AMD/requirejs: Define the module
    else if (typeof define === 'function' && define.amd) {
        define(function () {return en;});
    }
    // Browser: Expose to window
    else {
        window.en = en;
    }
})();