var gulp = require('gulp');
var sass = require('gulp-sass');
var uglify = require('gulp-uglify');
var rename = require('gulp-rename');
var ngAnnotate = require('gulp-ng-annotate');

gulp.task('compress-tinycolor', function () {
    return gulp.src('static/web/lib/tinycolor.js')
        .pipe(uglify())
        .pipe(rename(function (path) {
            path.basename += '.min';
        }))
        .pipe(gulp.dest('static/web/lib/'));
});

gulp.task('ng-annotate', function () {
    return gulp.src('js/*.js')
        .pipe(ngAnnotate())
        .pipe(gulp.dest('js'));
});

gulp.task('compress-js', function () {
    return gulp.src('js/*.js')
        .pipe(uglify())
        .pipe(rename(function (path) {
            path.basename += '.min';
        }))
        .pipe(gulp.dest('static/web/js/'));
});

gulp.task('sass', function () {
    gulp.src('scss/*.*')
        .pipe(sass({
            includePaths: 'node_modules/bootstrap-sass/assets/stylesheets',
            outputStyle: 'compressed'
        }).on('error', sass.logError))
        .pipe(rename(function (path) {
            path.basename += '.min';
        }))
        .pipe(gulp.dest('static/web/css/'));
});

// Watch tasks
gulp.task('default', function () {
    gulp.watch('js/*.js', ['compress-js']);
    gulp.watch('scss/*.*', ['sass']);
});
