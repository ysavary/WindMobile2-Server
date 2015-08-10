var gulp = require('gulp');
var gutil = require('gulp-util');
var source = require('vinyl-source-stream');
var buffer = require('vinyl-buffer');

var sass = require('gulp-sass');
var ngAnnotate = require('gulp-ng-annotate');
var browserify = require('browserify');
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');

gulp.task('ng-annotate', function () {
    return gulp.src(['static/web/js/app.js', 'static/web/js/controllers.js', 'static/web/js/services.js'])
        .pipe(ngAnnotate())
        .pipe(gulp.dest('js'));
});

gulp.task('js', function () {
    var bundle = browserify(
        ['static/web/js/app.js', 'static/web/js/controllers.js', 'static/web/js/services.js'],
        {debug: true}
    ).bundle();

    return bundle
        .pipe(source('windmobile.js'))
        .pipe(buffer())
        .pipe(sourcemaps.init({loadMaps: true}))
        .pipe(uglify())
        .on('error', gutil.log)
        .pipe(sourcemaps.write('./'))
        .pipe(gulp.dest('static/web/js/'));
});

gulp.task('sass', function () {
    gulp.src('scss/*.*')
        .pipe(sourcemaps.init())
        .pipe(sass({
            includePaths: 'node_modules/bootstrap-sass/assets/stylesheets',
            outputStyle: 'compressed'
        }).on('error', sass.logError))
        .pipe(sourcemaps.write('./'))
        .pipe(gulp.dest('static/web/css/'));
});

// Watch tasks
gulp.task('default', function () {
    gulp.watch('static/web/js/*.js', ['js']);
    gulp.watch('scss/*.*', ['sass']);
});
