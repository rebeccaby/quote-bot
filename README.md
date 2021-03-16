# Quote Bot

### To-Do:
- [ ] Design entity format (what is needed for the embedded messages)
- [ ] Create and store "quote" documents
- [ ] `$q "quote"` -> manually-written quote by author
- [ ] `$q message-link` -> linked message from user
- [x] `$q @user` -> last sent message from user
- [ ] $help command
- [ ] Scrollable embedded db documents via emoting
- [ ] Some quote fetch feature
- [x] Music bot, why not
- [ ] Allow adding playlists to queue
- [x] Add conditions to `$pause` and `$resume` to see if already paused/resumed

### Bugs:
  * Quote Bot's responses triggered else cond in $q command

### Future:
  * Test-bot for testing all commands (change Petey-bot, maybe)
  * Error-checking for (1) user has sent a message before (2) a user is pinged after $quote
  * Scroll through embedded quote cards with emotes (like Mudae)
  * Have "title" field in each document?
  * Implement cogs
  * Separate command for adding video playlist

### Improbable:
  * `$q @user "quote"` -> manually-written quote by pinged user (possibly use `greedy`?)