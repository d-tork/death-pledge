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