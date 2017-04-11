module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    nggettext_extract: {
      pot: {
        options: {
        },
        files: {
          'po/template.pot': ['static/*.html']
        }
      },
    },
    nggettext_compile: {
      all: {
        files: {
          'static/translations.js': ['po/*.po']
        }
      },
    },
  });

  grunt.loadNpmTasks('grunt-angular-gettext');

};
