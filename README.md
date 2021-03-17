# Quote Bot

### To-Do:
- [ ] Design entity format (what is needed for the embedded messages)
- [x] Create and store "quote" documents
- [ ] `$quote "quote"` -> manually-written quote by author
- [ ] `$quote message-link` -> linked message from user
- [x] `$quote @user` -> last sent message from user
- [ ] $help command
- [ ] Scrollable embedded db documents via emoting
- [ ] Some quote fetch feature
- [x] Music bot, why not
- [x] Allow adding songs to queue
- [x] Add conditions to `$pause` and `$resume` to see if already paused/resumed
- [ ] Add console messages for each command

### Bugs:
  * ~~Quote Bot's responses triggers else condition in $q command~~
    * Added check to see if bot ID is the same as the author ID
  * ~~Check if `$quote @user` author is the same as `@user`~~
    * Doesn't matter, skipped last message in channel's history anyway
  * `$quote arg` breaks if there's one quotation mark

### Future:
  * Test-bot for testing all commands (change Petey-bot, maybe)
  * Error-checking for (1) user has sent a message before (2) a user is pinged after $quote
  * Scroll through embedded quote cards with emotes (like Mudae)
  * ~~Have "title" field in each document?~~
  * Implement cogs
  * Separate command for adding video playlist
  * Utilize env vars instead of txt
  * Deploy (AWS?)
  * Use reactions for quote commands

### Improbable:
  * `$quote @user "quote"` -> manually-written quote by pinged user (possibly use `greedy`?)
  * Website to show all quotes