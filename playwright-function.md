yenupam
=======
- get_home_feed(): scrapes logged in x.com for posts by other users. and struture it in a pydantic model.
- get_post_data(return-value-of-get-home-feed): for returning full post text alogn with list of replies (replies w multiple replies are chained together in a nested list)
- post(): posts on https://x.com/compose/post
- like(status-id): like a status id
- repost():
ogbox
=====
- get_profile_stats(): https://x.com/{user} for updating follower, following counts (for my profile) and getting stats of other profiles
- quote(): clicks on quote button and adds a text
- reply(status-id): reply on a status id
- edit_profile(): https://x.com/settings/profile for updating name, bio, location, website
