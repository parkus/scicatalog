scicatalog
----------

A module containing a single class for handling catalogs of scientific data in a way that is easily extensible. 

Currently (2015/07/09) the SciCatalog class handles catalogs of values, their positive and negative uncertainties, and references for those values with methods for easily adding columns and changing values. The catalog is also backed up every time it is loaded under the assumption that it is being loaded so that it might be modified. 

Functionality is pretty minimal at the moment. I created this just to be able to record property of stars that I study.

SciCatalogs are not intended to handle large or even moderately sized databases. Specifically, I have prioritized preserving data with prolific backups and by saving to disk every time a value is changed using the object methods versus speed.

Written by Parke Loyd, 2015/07.
