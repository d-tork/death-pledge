### What will one instance of your class represent?
* One house

### What information should each instance have as instance variables?
* Each instance represents one house, and each house has:
  * price
  * address
  * room count
  * square footage
  * walk score
  * parking
  * laundry
  * year built
  * all variables as tuples, where var[0] is the actual value and var[1] is the rating on a 1-3 or 1-5 scale
    * this, at least for variables that need to be rated (like price, room count, year built) vs. non-rated (address)

### What instance methods should each instance have?
* get distance to nearest metro and/or bus stop
* get commuting times to work
* get distance to nearest grocery store
* compare to other property
* calculate monthly price

### What should the printed version of an instance look like? 
* Something like "Neighborhood - City, State - price - overall score"

## Sample: 
```python

class SampleObject(object):
    """Summary line should fit on one line.

    More text. Document public attributes in an ``Attributes`` section.

    Attributes:
        attr1 (str): Description of `attr`.
        attr2 (:obj:`int`, optional): Description of `attr2`.

    """

    def __init__(self, param1, param2, param3):
        """Example of docstring on the __init__ method.

        Note:
            Do not include the `self` parameter in the ``Args`` section.

        Args:
            param1 (str): Description of `param1`.
            param2 (:obj:`int`, optional): Description of `param2`. Multiple
                lines are supported.
            param3 (:obj:`list` of :obj:`str`): Description of `param3`.

        """
        self.attr1 = param1
        self.attr2 = param2
        self.attr3 = param3  # Doc comment *inline* with attribute

        # list of str: Doc comment *before* attribute, with type specified
        self.attr4 = ['attr4']

    @property
    def readonly_property(self):
        """str: Properties should be documented in their getter method."""
        return 'readonly_property'

    def example_method(self, param1, param2):
        """Class methods are similar to regular functions.

        Returns:
            True if successful, False otherwise

        """
        return True


def recalculate_scores():
    """Refresh data from all sources and re-score the listings.

    This will take into account several things that may change:
        -New data from the site, be it a change in price, status, 
        days-on-market, etc.
        -Updates to my ratings of the particular house.
        -Updates to my weightings of particular features for all houses.

    It should also sort by overall score and discard (or handle in some way)
    any listings that are absolutely and permanently off the market. No sense
    in seeing them anymore, except as a reference point for context. 

    """
    # Pull from google sheet (listings *and* weightings)
    # Run the scraper
    # Recalculate using functions from some other module
    # Store the results in a table, but without overwriting. I.e., timestamp
    #   that row and save it all to show changes
    # Write to google sheets


class Locality(object):
    """ Neighborhood / subdivision attributes and ratings

    A house belongs to a ZIP < Locality < City < State. This class exists 
    because localities share important attributes, such as:
        -access to public transit
        -demographics
        -median home price, income
        -crime statistics

    """

    def __init__(self, name):
        self.name = name


class HomeObject(object):
    """A home for sale.

    """

    def __init__(self, address):
        self.address = address  # instance variable
        self.visited = False

    def visit(self, rating_sheet):
        """Marks the home as visited.

        Weights it differently, given that I've seen the house and neighborhood
        with my own eyes.

        Args:
            rating_sheet (dict-like or Series): scores on various criteria

        """
        self.visited = True
        # Whatever the rating input may be, transform it into a better format
        self.visit_scores = rating_sheet
        # or upload it to google (if I haven't already...I might just enter it
        # directly there, and have it pulled in this program)
        
        recalculate_scores()

    def plan_visit(self):
        """Help guide my visit to fill in missing values.

        Check for any attributes that are missing values, or else are outliers
        (very high or low scores when the rest of the scores aren't so
        polarized). I want to retrieve or verify those in person.
        
        Also, I should be grading the photos on the website (as a whole, not 
        individually), so that I can be reminded to take my own photos of 
        certain features.

        """
        
    def get_price_context(self, other=None):
        """Compare this home's price to itself or others.

        A home price, in context, means:
            -its history of property values, former sales, price adjustments
            -its relation to home prices in the same area (street, ZIP, or
            locality)
            -a direct comparison to another (optional) specified house or 
            locality

        This ought to include line charts for changes over time, strip plot or
        histogram for distributions and outliers, and scatterplots for comparing
        price to various other attributes (e.g. how much does price correlate
        with square footage). Bonus: geographic heat maps?

        If possible, take a look into investment value here. I.e. are house 
        prices in this area on the rise? When, if ever, did they peak? This will
        be a major undertaking. 

        """
        # Compare to its immediate area: is this the most expensive house on 
        # the block? Is it the cheapest?

        # Compare to itself: has the price changed? How much was it originally
        # bought for? How long has it been at that price? 

        # Compare to others of the same category in my own data set (i.e. the
        # houses I've already looked at): am I relaxing my standards? Getting
        # desperate? 

        # Go and collect statistics on the neighborhood and surrounding area, 
        # most likely from Zillow (where scraping may be free and easy to do 
        # in bulk.
        return

    def show_summary(self):
        """Print or save a nice, concise rollup of all pertinent info.

        This is the quick-glance, not the deep-dive. What do I need to know: 
        the vitals, a short history, whether to pounce or not, the scores for
        the highest priority attributes. 

        Potentially list the one or two **currently active** houses that are
        close in overall score, and the one or two nearest geographically 
        (within a certain radius).
        """


class Condo(HomeObject):
    """ ...
    
    Price point/weighting scheme will be different, as will the expectations
    for:
        -square footage
        -number of rooms
        -distances / commute times
        -presence of garage, parking, and yard
    """
    structure_type = 'condo'  # class variable


class Detached(HomeObject):
    """ ...

    """
    structure_type = 'detached'
```
