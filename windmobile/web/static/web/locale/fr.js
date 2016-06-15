(function () {
    fr = {
        'Center': "Centrer",
        'List': "Liste",
        'Map': "Carte",
        'Help': "Aide",
        'Sign up': "Inscription",
        'Wind': "Vent",
        'Gust': "Rafale",
        'Temperature': "Température",
        'Humidity': "Humidité",
        'Pressure': "Pression",
        'Rain': "Pluie",
        'Summary': "Résumé",
        'last hour': "dernière heure",
        'Minimum': "Minimum",
        'Mean': "Moyen",
        'Maximum': "Maximum",
        'Summit': "Sommet",
        'Plain': "Plaine",
        'no recent data': "pas de donnée récente",
        'meters': "mètres",
        'Location service is disabled': "Service de localisation désactivé",
        'Unable to find your location': "Votre position n’a pu être déterminée",

        'HELP_STATION_SUMMARY_TITLE': "Affichage résumé d'une balise",
        'HELP_STATION_NAME': "Nom de la balise",
        'HELP_ALTITUDE': "Altitude",
        'HELP_LAST_UPDATE': "Date et validité des mesures",
        'HELP_PROVIDER': "Nom du fournisseur des données",
        'HELP_STATION_SUMMARY_TEXT_1_RED_DATE': "Date en rouge: ",
        'HELP_STATION_SUMMARY_TEXT_1_RED': "les mesures ont plus de 2 heures ou la balise n'est pas opérationnelle",
        'HELP_STATION_SUMMARY_TEXT_1_ORANGE_DATE': "Date en orange: ",
        'HELP_STATION_SUMMARY_TEXT_1_ORANGE': "les mesures datent d'il y a 1 ou 2 heures ou la balise n'est pas fiable",
        'HELP_STATION_SUMMARY_TEXT_2': "Dernière mesure du vent moyen et de la rafale",
        'HELP_STATION_SUMMARY_TEXT_3': "Tendance: historique du vent moyen durant la dernière heure",
        'HELP_STATION_SUMMARY_TEXT_4': "Historique de la direction du vent: du centre du cercle (il y a 1 heure) " +
        "vers l'extéreur (dernière mesure)",
        'HELP_STATION_DETAIL_TITLE': "Affichage détaillé d'une balise",
        'HELP_STATION_DETAIL_TEXT_1': "Centrer la carte sur cette balise",
        'HELP_STATION_DETAIL_TEXT_2': "Afficher les balises environnantes en mode liste",
        'HELP_IFRAME_TITLE': "Ajouter winds.mobi à votre site",
        'HELP_IFRAME_TEXT': "winds.mobi peut-être intégré dans un site existant à l'aide d'une iframe. " +
        "Vous pouvez fixer le point de recherche ou la position de la carte avec les paramètres 'lat', 'lon' et 'zoom'.",
        'HELP_MAP_COLORS_TITLE': "Couleurs des balises en mode carte",
        'HELP_MAP_COLORS_TEXT': "Rafale [km/h]",
        'HELP_PROVIDERS_TITLE': "Liste des fournisseurs de données",
        'HELP_COMPATIBILITY_TITLE': "Compatibilité",
        'HELP_COMPATIBILITY_TEXT': "winds.mobi fonctionne sur les dernières versions des principaux navigateurs web " +
        "(mobile ou bureau).",
        'HELP_CONTACT_TITLE': "À propos",
        'HELP_CONTACT_TEXT': "Des questions, problèmes ou idées d'amélioration ? Contactez-moi !",
        'SIGN_UP_SUMMARY_TITLE': "Créer votre compte winds.mobi",
        'SIGN_UP_TEXT': "Sauvegarder vos balises en créant votre compte winds.mobi avec Google ou Facebook.",
        'MY_LIST_EMPTY': "Votre liste est vide ! Ajouter une balise en cliquant sur son icône favoris depuis la vue 'détail'.",

        'N': "N",
        'NE': "NE",
        'E': "E",
        'SE': "SE",
        'S': "S",
        'SW': "SO",
        'W': "O",
        'NW': "NO"
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