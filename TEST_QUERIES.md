# Test Queries Reference
## Semantic Media Engine E2E Testing

Quick reference guide for manual testing with expected results.

## Book Queries

### Mystery/Detective
**Query:** `mystery book with detective`
**Expected Top Results:**
- The Mystery of the Blue Train (Agatha Christie)
- Sherlock (if TV shows included)
- The Silent Patient

**Query:** `psychological thriller`
**Expected Top Results:**
- The Silent Patient
- 1984
- Breaking Bad (TV)

### Romance
**Query:** `romantic love story period drama`
**Expected Top Results:**
- Pride and Prejudice
- The Seven Husbands of Evelyn Hugo

### Fantasy
**Query:** `fantasy magic mythology`
**Expected Top Results:**
- Circe
- The Invisible Life of Addie LaRue
- The Song of Achilles

### Science Fiction
**Query:** `science fiction space adventure`
**Expected Top Results:**
- Project Hail Mary
- 1984
- The Witcher (TV)

### Non-Fiction
**Query:** `memoir personal growth education`
**Expected Top Results:**
- Educated
- Atomic Habits


## TV Show Queries

### Science Fiction
**Query:** `science fiction show about time travel`
**Expected Top Results:**
- Dark
- Stranger Things

**Query:** `post apocalyptic survival`
**Expected Top Results:**
- The Last of Us
- The Mandalorian

### Drama
**Query:** `crime drama drug dealer`
**Expected Top Results:**
- Breaking Bad
- Succession

**Query:** `historical royal family`
**Expected Top Results:**
- The Crown
- Game of Thrones

### Fantasy
**Query:** `fantasy medieval dragons`
**Expected Top Results:**
- Game of Thrones
- The Witcher

**Query:** `monster hunter fantasy`
**Expected Top Results:**
- The Witcher

### Comedy
**Query:** `workplace comedy office`
**Expected Top Results:**
- The Office
- Ted Lasso

**Query:** `heartwarming optimistic comedy`
**Expected Top Results:**
- Ted Lasso
- The Office


## Mixed Media Queries

**Query:** `mystery investigation crime`
**Expected Results:** Mix of mystery books and crime TV shows

**Query:** `epic adventure fantasy`
**Expected Results:** Fantasy books and TV shows

**Query:** `psychological dark thriller`
**Expected Results:** Thrillers across both media types

## Edge Cases

### Minimum Length
**Query:** `ab` (2 characters)
**Expected:** No API call, helper text shown

**Query:** `abc` (3 characters)
**Expected:** API call made, results returned

### Empty Results
**Query:** `quantum physics advanced mathematics textbook`
**Expected:** "No recommendations found" message

### Special Characters
**Query:** `mystery!!! with @detective #crime`
**Expected:** Same results as "mystery detective crime"

### Long Query
**Query:** (500+ characters describing a very specific scenario)
**Expected:** Results returned normally, no truncation

## Performance Test Queries

**Query:** `drama`
**Expected:** Fast response (< 100ms)

**Query:** `science fiction time travel parallel universe quantum mechanics`
**Expected:** Response within 200ms

## Validation Tests

### Invalid top_k
**Request:** `{"query": "mystery", "top_k": 0}`
**Expected:** 422 Validation Error

**Request:** `{"query": "mystery", "top_k": 100}`
**Expected:** 422 Validation Error

### Empty Query
**Request:** `{"query": "", "top_k": 5}`
**Expected:** 422 Validation Error
