require 'bootstrap-sass'

sass_dir = 'scss'
css_dir = 'static/web/css'
javascripts_dir = 'static/web/js'
images_dir = 'static/web/images'
fonts_dir = 'static/web/fonts'

output_style = (environment == :production) ? :compressed : :expanded