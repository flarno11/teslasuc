# teslasuc

## Translations
### Preparation
- Install nodejs, grunt
- `npm install`

### Extract translations
    PATH=$PATH:./node_modules/.bin grunt nggettext_extract

### Translate
https://angular-gettext.rocketeer.be/dev-guide/translate/

### Compile translations
PATH=$PATH:./node_modules/.bin grunt nggettext_compile