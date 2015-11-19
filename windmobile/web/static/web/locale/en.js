(function () {
    en = {
        'Center': "Center",
        'List': "List",
        'Map': "Map",
        'Help': "Help",
        'Wind': "Wind",
        'Gust': "Gust",
        'Temperature': "Temperature",
        'Humidity': "Humidity",
        'Pressure': "Pressure",
        'Rain': "Rain",
        'Summary': "Summary",
        'last hour': "last hour",
        'Minimum': "Minimum",
        'Mean': "Mean",
        'Maximum': "Maximum",
        'Summit': "Summit",
        'Plain': "Plain",
        'no recent data': "no recent data",
        'meters': "meters",
        'Unable to find your location': "Unable to find your location",

        'HELP_STATION_SUMMARY_TITLE': "Station summary display",
        'HELP_STATION_NAME': "Station name",
        'HELP_ALTITUDE': "Altitude",
        'HELP_LAST_UPDATE': "Date and measure validity",
        'HELP_PROVIDER': "Data provider name",
        'HELP_STATION_SUMMARY_TEXT_1_RED_DATE': "Red date: ",
        'HELP_STATION_SUMMARY_TEXT_1_RED': "measures are older than 2 hours or the station is not operational",
        'HELP_STATION_SUMMARY_TEXT_1_ORANGE_DATE': "Orange date: ",
        'HELP_STATION_SUMMARY_TEXT_1_ORANGE': "measures are between 1 and 2 hours old or the station is not accurate",
        'HELP_STATION_SUMMARY_TEXT_2': "Last mean wind and gust wind measure",
        'HELP_STATION_SUMMARY_TEXT_3': "Trend: last hour mean wind historic",
        'HELP_STATION_SUMMARY_TEXT_4': "Wind direction historic: from circle center (1 hour ago) " +
        "to outside (last measure)",
        'HELP_MAP_COLORS_TITLE': "Station colors in map view",
        'HELP_MAP_COLORS_TEXT': "Wind gust [km/h]",
        'HELP_PROVIDERS_TITLE': "Data providers list",
        'HELP_COMPATIBILITY_TITLE': "Compatibility",
        'HELP_COMPATIBILITY_TEXT': "winds.mobi runs on the latest versions of the major browsers (mobile or desktop)",
        'HELP_CONTACT_TITLE': "About",
        'HELP_CONTACT_TEXT': "Questions, issues or improvement ideas ? Please contact me !",

        'N': "N",
        'NE': "NE",
        'E': "E",
        'SE': "SE",
        'S': "S",
        'SW': "SW",
        'W': "W",
        'NW': "NW"
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