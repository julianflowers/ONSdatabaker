Note - not extensively tested yet so it's as-is for the moment, let me know if you encounter any issues.

# ONSdatabaker
Excel Output Transformation language developed for the UK's Office of National Statistics. Branched from the original "databaker" repository for the continuation of development.

Originally developed by ScraperWiki Ltd https://scraperwiki.com/

Original documentation at http://scraperwiki.github.io/eot-docs/. Ongoing documentation to be added to these pages.

Note - pip installer added. ```pip install ONSdatabaker```

## Usage

Exactly the same as the original databaker with one exception. In you recipes, replace the line:

```from databaker.constants import *```

with

```from ONSdatabaker.constants import *```
