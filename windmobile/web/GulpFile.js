var gulp = require('gulp');
var gutil = require('gulp-util');
var source = require('vinyl-source-stream');
var buffer = require('vinyl-buffer');

var sass = require('gulp-sass');
var ngAnnotate = require('gulp-ng-annotate');
var browserify = require('browserify');
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');
var disc = require("disc");

gulp.task('fix-angular-src-for-browserify', function () {
    return gulp.src(['static/web/js/app.js', 'static/web/js/controllers.js', 'static/web/js/services.js'])
        .pipe(ngAnnotate())
        .pipe(gulp.dest('static/web/js/'));
});

gulp.task('js', function () {
    var bundle = browserify(
        ['static/web/js/app.js', 'static/web/js/controllers.js', 'static/web/js/services.js'],
        {debug: true}
    ).bundle();

    return bundle
        // http://stackoverflow.com/questions/23161387/catching-browserify-parse-error-standalone-option
        .on('error', function (err) {
            gutil.log(err);
            this.emit('end');
        })
        .pipe(source('windmobile.js'))
        .pipe(buffer())
        .pipe(sourcemaps.init({loadMaps: true}))
        .pipe(gutil.env.production ? uglify() : gutil.noop())
        .on('error', gutil.log)
        .pipe(sourcemaps.write('./'))
        .pipe(gulp.dest('static/web/js/'));
});

gulp.task('sass', function () {
    gulp.src('scss/*.*')
        .pipe(sourcemaps.init())
        .pipe(sass({
            includePaths: ['node_modules/bootstrap-sass/assets/stylesheets', 'node_modules/ng-toast/src/styles/sass'],
            outputStyle: 'compressed'
        }).on('error', sass.logError))
        .pipe(sourcemaps.write('./'))
        .pipe(gulp.dest('static/web/css/'));
});

gulp.task('discify', function (cb) {
    var b = browserify(
        ['static/web/js/app.js', 'static/web/js/controllers.js', 'static/web/js/services.js'],
        {fullPaths: true}
    );
    b.bundle()
        .pipe(disc())
        .pipe(source('index.html'))
        .pipe(gulp.dest('./disc'))
        .once('end', function () {
            cb();
        });
});

gulp.task('watch', function () {
    gulp.watch(['static/web/js/app.js', 'static/web/js/controllers.js', 'static/web/js/services.js'], ['js']);
    gulp.watch('scss/*.*', ['sass']);
});
gulp.task('default', ['js', 'sass']);
