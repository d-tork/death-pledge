# TODO 

- [x] rename 'change_from_initial' to 'change', then 'pct_change'
- [ ] score the % change from initial price? 
- [x] move 'sold' date to before 'sale_price'
- [x] move 'sold', 'sale_price', and 'sale_diff_pct' to end of dataframe
- [x] add % diff between tax assessed value and current price
    - [ ] and score it
- [ ] metro walk score should probably be weighted a little bit higher than commute score (or at least
higher than it is now), because metro walk is applicable to everyone (not just me) and at all times (not
just early morning), and my commute will feasibly change (maybe even to a driving commute in the opposite
direction, like Belvoir or McLean) yet the metro walk will still be valuable.
- [x] price and price per sqft definitely need to be weighted higher, or else commute's weight be reduced.
See: the DC property for $550K that made it in the top 10 despite being the most expensive house I've
analyzed AND in D.C.
- [ ] score the impact/importance of local driving times: how many times per week or month do I go to each
destination (e.g., the weekly drive to volleyball is more important than the bi-monthly trip to Sam's Club)
- [ ] create visitation sheet in google with the fields that I would rate in person. Then read that sheet
in, condense it down to a single number or two, and factor it into the scorecard. It can (and often should)
be negative, as this is an adjustment of my first impression. Internal to this manual assessment is a
weighting scheme, where the neighborhood and modernity threshold should be weighted quite heavily (considering
there's not much information available to to me on those things prior to the visit). 
- [ ] get and score the availability of grocery stores and department stores. Should be weighted pretty low
(considering I can resume a normal person's grocery shopping habits I suppose). 
- [ ] add a verdict field where I can say yay or nay and overrule the total score ranking and the sold
badge (essentially it would become inactive even when not sold. _Ideally_ I would find where the ranking went
wrong, but sometimes it's as simple as I hate everything about the layout of the house, but that can't be
represented in data avilable to me.
    - the question then becomes: how do I deal with those no's properly? Removed from the list? Score
    reduced to zero? Or just greyed out and left out of the "active" filter view?
- [x] add JBAB to local driving (to balance out Myer and Belvoir)
- [x] consider, instead of bus walk distance (although I really like that measure), it should be the walk
distance for the first leg of the trip regardless of what the destination is. Because a few of these
listings are getting by with 0-min bus stop walks simply because the first leg of the trip isn't to a bus
stop, it's straight to the metro. However, that walk is 20-30 minutes and if that's the reality of the
daily commute (30 min walking, 5 min metro ride) then that's a bit of a problem. 

