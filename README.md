# teslasuc

## Translations
### Preparation
- Install npm
- `npm install grunt --save-dev`
- `npm install grunt-angular-gettext --save-dev`

### Extract translations
    PATH=$PATH:./node_modules/.bin grunt nggettext_extract

### Translate
https://angular-gettext.rocketeer.be/dev-guide/translate/

### Compile translations
    PATH=$PATH:./node_modules/.bin grunt nggettext_compile