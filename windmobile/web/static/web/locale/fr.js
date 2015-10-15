(function () {
    fr = {
        "Center": "Centrer",
        "List": "Liste",
        "Map": "Carte",
        "Help": "Aide",
        "Wind": "Vent",
        "Temperature": "Température",
        "Humidity": "Humidité",
        "Pressure": "Pression",
        "Rain": "Pluie",
        "Summary": "Résumé",
        "last hour": "dernière heure",
        "Minimum": "Minimum",
        "Mean": "Moyenne",
        "Maximum": "Maximum",
        "Summit": "Sommet",
        "Plain": "Plaine",
        "no recent data": "pas de donnée récente",
        "meters": "mètres",
        "Unable to find your location": "Votre position n’a pu être déterminée"
    };

    // Node: Export function
    if (typeof module !== "undefined" && module.exports) {
        module.exports = fr;
    }
    // AMD/requirejs: Define the module
    else if (typeof define === 'function' && define.amd) {
        define(function () {return fr;});
    }
    // Browser: Expose to window
    else {
        window.fr = fr;
    }
})();