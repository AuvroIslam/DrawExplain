# Lesson transcripts: L4

Backend 3e13ede (Add CPU scheduling and page replacement solvers). + CPU scheduling and page replacement solvers.
Every lesson of the benchmark, as the student hears it (narration) and sees it (board text, sketch), with the automatic checks. Board texts attached to a lettered node show the letter first. Made by backend/scripts/eval_lessons.py.

## dijkstra_AtoE, run 1

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 5/5 (init PASS, relax_A PASS, relax_I_all PASS, order PASS, answer PASS). Lesson 23.206 s, 6 steps, model gpt-5.5.

**Shortest Path from A to E**: We run Dijkstra’s algorithm on this graph starting at A and stop as soon as E is finalized. The shortest route is found by repeatedly choosing the smallest tentative distance and relaxing its outgoing edges.

1. **Orient: what we’re solving**: You asked for the shortest path from A to E. This page is Dijkstra’s algorithm, so we’ll start at A, keep the cheapest known distances, and stop when E is locked in.
2. **Iteration 1: finalize A**: First rule: pick the unvisited vertex with the smallest tentative distance. A starts at 0, so A is finalized, and its direct neighbors get their first distances from A.
   - board: `a: A 0 ✓` · `b: B ∞→5` · `g: G ∞→9` · `h: H ∞→18`
3. **Finish A’s relaxations**: A also connects to I with weight 1. That gives I distance 1, which is now the smallest unvisited distance on the board.
   - board: `I ∞→1` · `a -> ?: cost 1`
4. **Iteration 2: finalize I**: Now the smallest unvisited value is I at 1, so we finalize I. Relaxing from I improves C to 7, E to 3, and G from 9 down to 4.
   - board: `I 1 ✓` · `c: C ∞→7` · `e: E ∞→3` · `g: G 9→4`
5. **Iteration 3: finalize E and stop**: Next smallest is E at 3, so E is finalized. Since E is the target, Dijkstra stops right here: the final cost is 3.
   - board: `e: E 3 ✓`
6. **Answer: A → I → E**: So the shortest path is A to I to E: 1 plus 2 equals 3. Notice we did not need to explore the whole graph once E became finalized.
   - board: `a -> ?: 1` · `? -> e: 2` · `e: total = 3`
   - sketch: `flowchart LR ; A[Start A] ; Pick[Pick smallest] ; Relax[Relax edges] ; Echeck{E finalized?} ; Path[A-I-E] ; A --> Pick ; Pick --> Relax ; Relax --> Echeck ; Echeck -->\|no\| Pick ; Echeck -->\|yes\| Path`

## dijkstra_AtoE, run 2

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 5/5 (init PASS, relax_A PASS, relax_I_all PASS, order PASS, answer PASS). Lesson 23.919 s, 6 steps, model gpt-5.5.

**Shortest Path from A to E**: We’ll run Dijkstra’s algorithm on the graph shown, starting at A and stopping when E is finalized. The shortest route is discovered by repeatedly choosing the smallest tentative distance and relaxing its outgoing edges.

1. **Orient: start at A, aim for E**: To answer how to get from A to E, we’ll trace Dijkstra’s Algorithm on this graph. I’m circling the source A and the target E so our mission is clear.
2. **Initialize and finalize A**: Dijkstra starts with A at distance 0 and everything else at infinity. The smallest unvisited distance is A, so A becomes finalized first.
   - board: `a: A 0 ✓` · `b: B ∞` · `I ∞`
3. **Relax A’s four edges**: Now we update every neighbor of A using 0 plus the edge weight. That gives B 5, G 9, H 18, and I 1.
   - board: `b: B ∞→5` · `g: G ∞→9` · `h: H ∞→18` · `I ∞→1`
4. **Finalize I and relax from I**: Among unvisited vertices, I has the smallest tentative distance, 1, so we finalize I. From I, we improve C to 7, E to 3, and G from 9 down to 4.
   - board: `I 1 ✓` · `c: C ∞→7` · `e: E ∞→3`
5. **One more improvement: G**: Still from I, the edge to G has weight 3, so 1 plus 3 equals 4. Since 4 beats the old 9, G’s best known route now goes through I.
   - board: `g: G 9→4` · `? -> g: shorter route`
6. **Finalize E: shortest path found**: Now the smallest unvisited distance is E at 3, so Dijkstra finalizes E and we stop. Following predecessors gives A to I to E, total cost 1 plus 2 equals 3.
   - board: `e: E 3 ✓` · `a -> ?: 1` · `? -> e: 2`
   - sketch: `flowchart TD ; A[Start A=0] ; B[Pick smallest] ; C[Finalize vertex] ; D[Relax neighbors] ; E{Is E final?} ; F[Path A-I-E] ; A-->B ; B-->C ; C-->D ; D-->E ; E-->\|no\|B ; E-->\|yes\|F`

## dijkstra_AtoE, run 3

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 5/5 (init PASS, relax_A PASS, relax_I_all PASS, order PASS, answer PASS). Lesson 22.343 s, 6 steps, model gpt-5.5.

**Shortest Path from A to E**: We run Dijkstra’s algorithm on the graph, starting at A and stopping when E is finalized. The shortest path found is A → I → E with total cost 3.

1. **Orient: find the question on the graph**: We want the cheapest route from A to E, so this page’s graph is our workspace. I’ll circle the start and target, then we’ll let Dijkstra choose vertices by smallest current distance.
   - board: `a: A = 0`
2. **Iteration 1: finalize A and relax its neighbors**: Smallest tentative distance is A at zero, so A becomes final. From A, we write the first costs to B, G, H, and I using the printed edge weights.
   - board: `a: 0 ✓` · `b: B ∞→5` · `g: G ∞→9` · `h: H ∞→18`
3. **Finish A’s relaxations: I gets the best early lead**: One more neighbor of A matters a lot: the edge A to I has weight 1. That makes I the smallest unvisited distance, so it will be chosen next.
   - board: `I ∞→1` · `a -> ?: cost 1`
4. **Iteration 2: finalize I and improve nearby distances**: Now I has the smallest tentative distance, 1, so I becomes final. Relaxing from I gives C cost 7, E cost 3, and improves G from 9 down to 4.
   - board: `1 ✓` · `c: C ∞→7` · `e: E ∞→3` · `g: G 9→4`
5. **Iteration 3: finalize E, so we stop**: Among unvisited vertices, E now has the smallest tentative distance, 3. Because E is our target, finalizing it proves no later route can beat cost 3.
   - board: `e: 3 ✓ stop`
6. **Answer: A → I → E costs 3**: So the shortest path from A to E is A to I to E: 1 plus 2 equals 3. Dijkstra stops exactly when E is finalized, not when we merely first notice it.
   - board: `a -> ?: 1` · `? -> e: 2` · `e: 1+2=3`
   - sketch: `flowchart LR ; A[A dist 0] --> I[I dist 1] ; I --> E[E dist 3] ; E --> Stop[final stop]`

## tcp_cwnd, run 1

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 4/5 (starts_at_1 FAIL, doubling PASS, concrete_threshold PASS, additive PASS, timeout PASS). Lesson 23.862 s, 6 steps, model gpt-5.5.

**TCP Congestion Window Until Timeout**: This page explains how TCP’s CongWin grows in slow start, then additive increase, and drops on a timeout. We’ll run an illustrative example with ssthresh = 8 MSS to answer how the window changes over time.

1. **Find the three rules**: Your question lives in these three rules: start tiny, grow fast, then cut back on timeout. I’ll use an illustrative example because the slide gives rules but no starting threshold number.
2. **Slow start: 1 to threshold**: Set the example threshold to 8 MSS. In slow start, each RTT roughly doubles CongWin: rounds 1, 2, and 3 go 1 to 2 to 4 to 8.
   - board: `ssthresh = 8` · `cwnd 1→2→4→8` · `until threshold`
3. **Additive increase after threshold**: Once CongWin hits 8, the slide switches to additive increase. Now it rises gently by about 1 MSS per RTT: rounds 4 through 7 give 8, 9, 10, 11, then 12 entering round 8.
   - board: `8→9→10→11→12` · `after that`
4. **Timeout: multiplicative decrease**: At round 8, timeout happens while cwnd is 12 MSS. The timeout rule halves the threshold to 6, then resets CongWin all the way back to 1 MSS.
   - board: `12/2=6; cwnd=1`
5. **Growth restarts after timeout**: After the timeout reset, TCP slow-starts again, but toward the new threshold 6. So rounds 9 to 11 are cwnd 1, 2, 4, then capped at 6 before avoidance resumes.
   - board: `restart SS` · `new ssthresh=6` · `1→2→4→6`
6. **Plain answer**: So the example CongWin sequence is 1, 2, 4, 8, 9, 10, 11, 12, then timeout resets it to 1. Big pattern: exponential rise, linear rise, multiplicative drop.
   - board: `SS → AI → timeout`
   - sketch: `flowchart LR ; A[Start cwnd 1] --> B[Slow start] ; B --> C[Reach ssthresh] ; C --> D[Additive increase] ; D --> E[Timeout] ; E --> F[Set cwnd 1]`

Missing: starts_at_1: MISSING

## tcp_cwnd, run 2

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 5/5 (starts_at_1 PASS, doubling PASS, concrete_threshold PASS, additive PASS, timeout PASS). Lesson 23.99 s, 7 steps, model gpt-5.5.

**TCP CongWin: Start to Timeout**: This page explains how TCP’s congestion window grows first by Slow Start, then by Additive Increase, and finally drops on a timeout. We’ll answer the question by running an illustrative cwnd example directly from the rules on the slide.

1. **Orient: three phases**: This page answers your question in three moves: Slow Start grows fast, Additive Increase grows gently, and timeout triggers Multiplicative Decrease. I’ll circle the three rules we’ll run.
2. **Slow Start example**: The slide gives rules, not numbers, so here is an illustrative example: start with cwnd equal to 1 MSS and ssthresh equal to 8 MSS. In Slow Start, each ACK adds 1 MSS, so over RTTs the window doubles: 1 to 2 to 4 to 8.
   - board: `ssthresh = 8` · `cwnd 1→2→4→8`
3. **Reach the threshold**: By round 3, cwnd reaches the threshold value of 8, so Slow Start stops. That arrow shows the handoff: after this point, TCP switches to the gentler congestion-avoidance rule.
   - board: `reached at 8` · `then AI`
4. **Additive Increase rounds**: Now congestion avoidance adds only about 1 MSS per round trip, not doubling anymore. Starting at 8, the next rounds are 9, 10, 11, then 12 before the timeout happens.
   - board: `8→9→10→11→12`
5. **Timeout cuts the window**: At round 8, our example times out while cwnd is 12. The timeout rule halves the threshold to 6, then resets CongWin to 1 MSS.
   - board: `12/2 = 6` · `cwnd 12→1`
6. **After timeout, restart**: After the timeout, TCP starts Slow Start again, now aiming for the new threshold 6. So the next example rounds are 1, 2, 4, 6, and then Additive Increase resumes at 7.
   - board: `restart SS` · `new ssthresh = 6` · `1→2→4→6→7`
7. **Final answer**: So from the start until timeout, the congestion window goes 1, 2, 4, 8, 9, 10, 11, 12 MSS, then timeout drops it to 1. Big picture: grow fast, grow slowly, cut sharply.
   - sketch: `flowchart LR ; A[Start cwnd 1] --> B[Slow Start] ; B --> C[Reach ssthresh] ; C --> D[Additive Increase] ; D --> E[Timeout] ; E --> F[cwnd to 1]`

## tcp_cwnd, run 3

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 5/5 (starts_at_1 PASS, doubling PASS, concrete_threshold PASS, additive PASS, timeout PASS). Lesson 24.684 s, 6 steps, model gpt-5.5.

**TCP Congestion Window: Start to Timeout**: This page explains how TCP grows CongWin first with Slow Start, then Additive Increase, and cuts it on a timeout. We’ll run an illustrative example with ssthresh = 8 MSS to answer how the window changes.

1. **Find the three rules**: Your question lives in these three rules: grow fast, then grow gently, then drop on timeout. I’ll use an example with ssthresh = 8 MSS because the slide gives rules but no numbers.
   - board: `example: ssthresh=8`
2. **Slow Start doubles each RTT**: We start exactly where the slide says: CongWin = 1 MSS. In slow start, ACKs add 1 MSS each, so over each RTT the round values go 1 to 2 to 4 to 8.
   - board: `cwnd 1→2→4→8` · `until threshold`
3. **At threshold, switch to additive**: At cwnd = 8, we have reached ssthresh, so slow start stops. Now congestion avoidance takes over: the window rises by 1 MSS per RTT, giving 8, 9, 10, 11, 12.
   - board: `switch` · `cwnd 8→9→10→11→12`
4. **Timeout cuts the window**: Now the timeout happens at cwnd = 12. The slide’s timeout rule halves the threshold to 6 and resets CongWin all the way back to 1 MSS.
   - board: `12/2=6; cwnd=1`
5. **After timeout, start again**: Because CongWin reset to 1, TCP returns to slow start under the new ssthresh = 6. The next rounds are 1, 2, 4, then capped at 6, and after that additive gives 7.
   - board: `restart` · `new ssthresh=6` · `1→2→4→6` · `then 6→7`
6. **Answer: the full change sequence**: So the congestion window changes like this: 1, 2, 4, 8, 9, 10, 11, 12, then timeout drops it to 1. Big pattern: exponential growth, linear growth, multiplicative decrease.
   - sketch: `flowchart LR ; A[Start cwnd 1] --> B[Slow start] ; B --> C[Reach ssthresh] ; C --> D[Additive increase] ; D --> E[Timeout] ; E --> F[Halve threshold] ; F --> G[Reset cwnd 1]`

## flowchart_invalid_twice, run 1

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 18.283 s, 5 steps, model gpt-5.5.

**Invalid Twice in the Validation Loop**: If the input is invalid twice, the flowchart takes the No branch twice: each time it shows an error and loops back to read input again. It only moves to Process data after a valid input passes the decision check.

1. **Find the loop that answers it**: Great question: invalid twice means we travel the retry loop twice. I’ll circle the decision where the input is judged, because every repeat starts from this Valid? check.
2. **First invalid input: take No**: On the first bad entry, the answer to Valid? is No. Follow my red arrow down: the flowchart tells us to show an error, not process the data yet.
   - board: `invalid #1` · `1st error`
3. **Loop back to read again**: After showing the error, the line loops back to Read input. That means the program asks again instead of ending or processing.
   - board: `ask again` · `try #2`
4. **Second invalid input: repeat the same path**: Now the second input is also invalid, so the same rule fires again: Valid? goes to No, then Show error. I’m marking this as the second trip around the loop.
   - board: `check #2` · `invalid #2` · `2nd error`
5. **Answer: two errors, still asking**: So if the input is invalid twice, the program shows the error twice and returns to Read input a third time. It will only follow Yes to Process data when an input finally passes.
   - board: `only when valid` · `next is try #3`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`

## flowchart_invalid_twice, run 2

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 14.563 s, 5 steps, model gpt-5.5.

**Invalid Twice in the Validation Loop**: If the input is invalid twice, the flowchart takes the “No” branch twice, shows the error twice, and returns to “Read input” each time. It only moves to “Process data” after a valid input is entered.

1. **Where the answer lives**: Great question: invalid twice means we follow the loop twice. I’ll circle the decision diamond because this is where each input gets tested.
   - board: `test each try`
2. **Attempt 1: invalid input**: First try: the program reads the input, then the answer to “Valid?” is No. Follow my red arrow down to the error box.
   - board: `No #1` · `error shown 1`
3. **Loop back after attempt 1**: After showing the error, the flow loops back to Read input. That means the program does not quit; it asks again.
   - board: `try again` · `attempt 2 starts`
4. **Attempt 2: invalid again**: Second try repeats the same rule: read, check, and if it is still invalid, take No again. So the error box runs a second time.
   - board: `check again` · `No #2` · `error shown 2`
5. **Final answer: still looping**: So if the input is invalid twice, the chart shows the error twice and returns to Read input twice. It stops looping only when Valid? becomes Yes, then it processes the data.
   - board: `when valid` · `after success`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`

## flowchart_invalid_twice, run 3

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 15.976 s, 6 steps, model gpt-5.5.

**Invalid Twice in a Validation Loop**: This flowchart keeps asking for input until the decision box says the input is valid. If the input is invalid twice, the No path runs twice, showing the error each time and looping back to read input again.

1. **Find the loop we will run**: Great question: if the input is invalid twice, we follow the No branch twice. This page is an input validation loop, and the answer lives around this decision diamond.
2. **Start by reading the first input**: We begin at Start, then read the user’s first input. I’ll mark that first attempt as try 1 before the decision checks it.
   - board: `try 1` · `attempt 1`
3. **First invalid input takes the No path**: Now the decision asks Valid?, and for the first invalid input the answer is No. Follow my red arrow down to Show error, because the program rejects that attempt.
   - board: `check` · `invalid`
4. **Loop back for the second try**: After showing the error, the flow does not end. This long return arrow sends us back to Read input, so the user gets a second try.
   - board: `ask again` · `attempt 2`
5. **Second invalid input repeats the same loop**: If the second input is invalid too, the exact same No path happens again. So we show the error a second time, then loop back again for another input.
   - board: `check 2` · `No again` · `error ×2`
6. **Answer: it keeps looping**: So after two invalid inputs: Read input, Show error, Read input, Show error, then ask again. It only moves to Process data when a later input passes the Valid? check.
   - board: `only when valid`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`

## math_calvin_cycle, run 1

Question: "How many ATP and NADPH does this cycle use to fix 3 CO₂, and what happens to the 6 GAP?" (math_calvin_cycle.png)
Score 5/5 (fixation PASS, reduction_cost PASS, regeneration_cost PASS, totals PASS, gap_split PASS). Lesson 19.893 s, 6 steps, model gpt-5.5.

**Calvin Cycle Cost and GAP Fate**: This page shows the Calvin cycle fixing 3 CO₂ into sugar-building GAP. For 3 CO₂, the cycle spends 9 ATP and 6 NADPH total; of the 6 GAP made, 1 GAP exits and 5 GAP are recycled to regenerate RuBP.

1. **Find the question on the cycle**: We’re tracking two things: the energy bill for fixing these 3 CO₂, and the fate of the 6 GAP. I’ll circle the carbon input and the GAP branch where the answer lives.
   - board: `product pool`
2. **First ATP spending: phosphorylation**: First, the cycle upgrades 6 molecules of 3-P-glycerate using ATP. Follow my red arrow: 6 ATP become 6 ADP, so that is the first energy cost.
   - board: `spent` · `ATP cost = 6`
3. **NADPH reduces the 6 intermediates**: Next, NADPH supplies high-energy electrons to reduce 1,3-bP-glycerate into GAP. The page shows 6 NADPH/H⁺ turning into 6 NADP⁺, and releasing 6 Pi.
   - board: `electrons used` · `NADPH cost = 6`
4. **The 6 GAP split: 1 exits, 5 recycle**: Here is the key GAP accounting: the cycle makes 6 GAP, but only one GAP leaves as net product. The other 5 GAP follow the lower path back into regeneration.
   - board: `1 exits` · `5 recycle` · `net sugar output`
5. **Second ATP spending: regeneration**: Those 5 recycled GAP are rearranged into 3 ribulose-5-P, then ATP re-phosphorylates them into 3 ribulose-1,5-bP. This regeneration step spends 3 more ATP.
   - board: `rearrange` · `spent`
6. **Total answer**: So the answer is: fixing 3 CO₂ uses 9 ATP total and 6 NADPH. The 6 GAP split into 1 GAP exported and 5 GAP recycled to rebuild the CO₂ acceptor.
   - board: `6 + 3 = 9 ATP`
   - sketch: `flowchart LR ; A[3 CO2 fixed] --> B[6 PGA] ; B --> C[6 GAP] ; C --> D[1 GAP exits] ; C --> E[5 GAP recycle] ; E --> F[3 RuBP rebuilt]`

## math_calvin_cycle, run 2

Question: "How many ATP and NADPH does this cycle use to fix 3 CO₂, and what happens to the 6 GAP?" (math_calvin_cycle.png)
Score 5/5 (fixation PASS, reduction_cost PASS, regeneration_cost PASS, totals PASS, gap_split PASS). Lesson 21.941 s, 6 steps, model gpt-5.5.

**ATP, NADPH, and the 6 GAP**: This Calvin-cycle diagram shows the cost to fix 3 CO₂ and the fate of the 6 GAP made. The cycle uses 9 ATP total and 6 NADPH; only 1 GAP leaves while 5 GAP regenerate the CO₂ acceptor.

1. **Find the carbon-fixing setup**: We’re answering: for these 3 CO₂, what energy is spent, and where do the 6 GAP go? I’ll circle the entry point and the first 6-carbon accounting split into six C3 molecules.
   - board: `fixation`
2. **Count the ATP used in reduction**: First energy bill: the six 3-P-glycerat molecules are phosphorylated. This arrow spends 6 ATP and gives 6 ADP, so we write ATP cost equals six here.
   - board: `ATP = 6`
3. **Count the NADPH used**: Next, 1,3-bP-glycerat is reduced to GAP. The diagram says 6 NADPH/H⁺ become 6 NADP⁺ plus 6 phosphate, so NADPH cost equals six.
   - board: `NADPH = 6`
4. **Split the 6 GAP products**: Now the key fate question: the cycle makes 6 GAP. One GAP peels off to the right, while five GAP stay in the cycle for rebuilding ribulose-5-P.
   - board: `1 exits` · `5 recycle`
5. **Regenerate the CO₂ acceptor**: Those five recycled GAP are rearranged into three ribulose-5-P, then ATP phosphorylates them back into ribulose-1,5-bP. That regeneration step uses 3 more ATP.
   - board: `rearrange` · `+3 ATP`
6. **Total cost and GAP answer**: So the answer is 9 ATP total: 6 here plus 3 here, and 6 NADPH total. Of the 6 GAP, 1 leaves as product and 5 regenerate the cycle.
   - board: `6+3=9 ATP`
   - sketch: `flowchart LR ; A[3 CO2 enter] --> B[6 PGA] ; B --> C[6 GAP] ; C --> D[1 GAP exits] ; C --> E[5 GAP recycle] ; E --> F[3 RuBP]`

## cs_bst_insert, run 1

Question: "How would you insert 5 into this binary search tree? Show the comparisons, where 5 ends up, and the in-order traversal afterwards." (cs_bst_insert.png)
Score 4/5 (left_at_8 PASS, right_at_3_left_at_6 PASS, right_child_of_4 FAIL, search_path PASS, inorder_after PASS). Lesson 25.238 s, 6 steps, model gpt-5.5.

**Inserting 5 in the BST**: We’ll follow the binary search tree rule: smaller values go left, larger values go right. Starting at 8, the comparisons place 5 as the left child of 6, and the in-order traversal becomes sorted.

1. **Orient: use the BST rule**: We’re inserting 5 into this binary search tree. I’ll start at the root I just circled: compare 5 to each node, then move left if smaller and right if larger.
   - board: `start here`
2. **Comparison 1: 5 is less than 8**: First comparison: 5 is less than 8, so we follow the left branch. That rule keeps every value in 8’s left subtree smaller than 8.
   - board: `5 < 8` · `go left`
3. **Comparison 2: 5 is greater than 3**: Now compare 5 with 3. Since 5 is greater than 3, we move right to 6, staying inside the left side of 8.
   - board: `5 > 3` · `go right`
4. **Comparison 3: insert left of 6**: At 6, 5 is smaller, so we try the left child. That spot is between 4 and 6 and is empty, so 5 lands there.
   - board: `5 < 6` · `go left` · `insert 5`
5. **Check the local order**: Quick sanity check: 4 is still left of 6, 7 is still right of 6, and new 5 belongs between them. So the tree rule is preserved.
   - board: `4 < 5 < 6`
6. **In-order traversal after insertion**: For in-order traversal, read left subtree, then node, then right subtree. After inserting 5, the final order is 1, 3, 4, 5, 6, 7, 8, 10, 13, 14.
   - board: `in-order` · `1,3,4,5,6,7,8,10,13,14`
   - sketch: `flowchart TD ; A[Compare at node] ; B{5 smaller?} ; C[Go left] ; D[Go right] ; E[Empty spot] ; F[Insert 5] ; A --> B ; B -->\|yes\| C ; B -->\|no\| D ; C --> A ; D --> A ; A --> E ; E --> F`

Missing: right_child_of_4: MISSING any: 0 of 6 matched, need 1

## cs_bst_insert, run 2

Question: "How would you insert 5 into this binary search tree? Show the comparisons, where 5 ends up, and the in-order traversal afterwards." (cs_bst_insert.png)
Score 5/5 (left_at_8 PASS, right_at_3_left_at_6 PASS, right_child_of_4 PASS, search_path PASS, inorder_after PASS). Lesson 20.089 s, 5 steps, model gpt-5.5.

**Insert 5 into the BST**: We’ll insert 5 by following binary-search-tree comparisons from the root: smaller goes left, larger goes right. Then we’ll read the tree in-order to verify the sorted result.

1. **Start at the root**: This is a binary search tree, and we’re inserting 5. Start at the root I just circled: compare 5 with 8, and because 5 is smaller, follow my arrow left.
   - board: `5 < 8` · `go left`
2. **Compare at 3**: Now we land on 3. Since 5 is bigger than 3, the BST rule sends us to the right child, toward 6.
   - board: `5 > 3` · `go right`
3. **Compare at 6**: At 6, 5 is smaller, so we go left. That left child is 4, so we keep comparing instead of inserting yet.
   - board: `5 < 6` · `go left`
4. **Find the empty spot**: Now at 4, 5 is larger, so we look to the right of 4. There is no node there, so 5 gets inserted as 4’s right child.
   - board: `5 > 4` · `insert` · `new node 5`
5. **In-order traversal result**: To get the in-order traversal, read left subtree, then node, then right subtree. With the new 5 tucked after 4 and before 6, the traversal is 1, 3, 4, 5, 6, 7, 8, 10, 13, 14.
   - board: `between 4 and 6` · `1,3,4,5,6,7,8,10,13,14`
   - sketch: `flowchart TD ; A[Compare at node] ; B{5 smaller?} ; C[Go left] ; D[Go right] ; E[Empty spot] ; F[Insert 5] ; A --> B ; B -->\|yes\| C ; B -->\|no\| D ; C --> A ; D --> A ; A --> E ; E --> F`

## cs_bfs_dfs, run 1

Question: "In which order does breadth-first search visit the nodes if it starts at A and takes neighbours in alphabetical order? How would depth-first search from A differ?" (cs_bfs_dfs.png)
Score 4/5 (bfs_order PASS, bfs_queue PASS, bfs_levels PASS, dfs_order FAIL, dfs_mechanism PASS). Lesson 27.341 s, 6 steps, model gpt-5.5.

**BFS vs DFS from A**: We’ll run breadth-first search exactly on this graph starting at A, using a FIFO queue and alphabetical neighbours. Then we’ll contrast how depth-first search would dive down one branch before coming back.

1. **Set the starting rule**: We start at A, and breadth-first search uses a FIFO queue: first in, first out. I’ll circle A and write the initial queue, because A is marked seen before any visiting happens.
   - board: `a: queue [A]`
2. **Visit A, enqueue level 1**: Now dequeue A and visit it first. Its alphabetical neighbours are B, C, E, so they enter the queue in that order as level 1 children of A.
   - board: `a: visit 1 ✓` · `b: seen, L1` · `c: seen, L1` · `e: queue [B,C,E]`
3. **Visit B, add D and F**: FIFO means B comes out next, not C or E yet. From B, the unvisited alphabetical neighbours are D then F, so both are marked and placed at the back.
   - board: `b: visit 2 ✓` · `d: seen, L2` · `f: seen, L2` · `queue [C,E,D,F]`
4. **Visit C, add G**: Next the queue front is C, so C is visited third. C’s only unvisited neighbour is G, so G joins after D and F, not before them.
   - board: `c: visit 3 ✓` · `g: seen, L2` · `queue [E,D,F,G]`
5. **Finish the BFS queue**: Now BFS simply drains the queue: E, then D, then F, then G. None adds a new unvisited node, so the BFS order is A, B, C, E, D, F, G.
   - board: `e: visit 4 ✓` · `d: visit 5 ✓` · `f: visit 6 ✓` · `g: visit 7 ✓`
6. **How DFS differs**: Depth-first search would use the same alphabetical choice, but it dives before siblings: from A to B to D, then backtrack to F, then C to G, then E. So DFS order is A, B, D, F, C, G, E.
   - board: `a -> b: DFS dives` · `BFS: A B C E D` · `DFS: A B D F C`
   - sketch: `flowchart TD ; A[Start A] --> B[BFS: queue] ; B --> C[Visit front] ; C --> D[Enqueue neighbours] ; D --> E[Queue empty?] ; E -->\|no\| C ; E -->\|yes\| F[Done]`

Missing: dfs_order: MISSING any: 0 of 2 matched, need 1

## cs_bfs_dfs, run 2

Question: "In which order does breadth-first search visit the nodes if it starts at A and takes neighbours in alphabetical order? How would depth-first search from A differ?" (cs_bfs_dfs.png)
Score 5/5 (bfs_order PASS, bfs_queue PASS, bfs_levels PASS, dfs_order PASS, dfs_mechanism PASS). Lesson 22.002 s, 6 steps, model gpt-5.5.

**BFS vs DFS from A**: We’ll run breadth-first search from A using a FIFO queue and alphabetical neighbours, then contrast it with the depth-first path choice. The BFS visit order is A, B, C, E, D, F, G; DFS differs because it goes deep before coming back.

1. **Start at A: queue first**: We’re answering the visit-order question by simulating BFS right on this graph. I’ll circle A: BFS starts with queue [A], and A is already seen before we visit anything.
   - board: `a: queue [A]` · `a: seen`
2. **Visit A, enqueue its neighbours**: Now we dequeue A, so A is visited first. Its alphabetical neighbours are B, C, E, so we mark and enqueue all three at level 1.
   - board: `a: 1 ✓` · `b: seen L1` · `c: seen L1` · `e: seen L1`
3. **Visit B, add D and F**: FIFO means B is next, because it entered the queue before C and E. From B, the new alphabetical neighbours are D then F, so the queue becomes [C, E, D, F].
   - board: `b: 2 ✓` · `d: seen L2` · `f: seen L2` · `b: Q [C,E,D,F]`
4. **Visit C, add G**: Next out of the FIFO queue is C. C has one unvisited neighbour, G, so G is marked level 2 and placed after F.
   - board: `c: 3 ✓` · `g: seen L2` · `c: Q [E,D,F,G]`
5. **Finish E, D, F, G**: Now the queue order settles the rest: E, then D, then F, then G. None adds a new unvisited node, so BFS ends with this full order.
   - board: `e: 4 ✓` · `d: 5 ✓` · `f: 6 ✓` · `g: 7 ✓`
6. **How DFS would differ**: So BFS visits A, B, C, E, D, F, G because it works by layers. DFS with alphabetical neighbours would instead dive: A, B, D, then back to F, E, then C, G.
   - board: `a -> b: DFS dives` · `a+b+c+e+d+f+g: DFS: A,B,D,F,E,C,G`
   - sketch: `flowchart TD ; A[Start A] --> B[Use FIFO] ; B --> C[Visit front] ; C --> D[Enqueue unseen] ; D --> E[Alphabetical order] ; E --> F[Queue empty] ; F --> G[BFS order]`

## cs_dijkstra_a_to_e, run 1

Question: "Use Dijkstra's algorithm starting at A: what are the shortest distances to the other nodes, and what is the shortest path from A to E?" (cs_dijkstra_a_to_e.png)
Score 5/5 (b_stays_4 PASS, d_is_5 PASS, e_is_10 PASS, path_a_c_e PASS, via_d_is_12 PASS). Lesson 21.51 s, 6 steps, model gpt-5.5.

**Dijkstra from A to E**: We run Dijkstra’s algorithm on the weighted graph starting at A. The shortest final distances are A=0, B=4, C=2, D=5, E=10, and the shortest path to E is A → C → E.

1. **Set up the distances**: We’ll answer this by running Dijkstra from A. I’m circling the start node, and every other node begins at infinity until an edge gives us a better route.
   - board: `a: A = 0` · `b: B = ∞` · `c: C = ∞`
2. **Iteration 1: finalize A**: The smallest tentative distance is A at 0, so A is finalized. Now relax A’s two edges: A to B gives 0+4, and A to C gives 0+2.
   - board: `a: ✓ done` · `b: B ∞→4` · `c: C ∞→2`
3. **Iteration 2: finalize C**: Among unvisited nodes, C has the smallest distance, 2, so C is finalized next. Relaxing from C keeps B at 4, improves D to 5 using the weight 3 edge, and sets E to 10.
   - board: `c: ✓ done` · `b: stays 4` · `d: D ∞→5` · `e: E ∞→10`
4. **Iterations 3 and 4: finalize B, then D**: Next smallest is B at 4, so B is finalized, but B to D would be 14, not better than 5. Then D is finalized; D to E would be 12, not better than 10.
   - board: `b: ✓ done` · `d: stays 5` · `d: ✓ done` · `e: stays 10`
5. **Iteration 5: finalize E and read the path**: Now E is the smallest unvisited node at 10, so E is finalized and we stop. Trace predecessors backward: E came from C, and C came from A, giving A to C to E.
   - board: `e: ✓ done` · `a -> c: cost 2` · `c -> e: cost 8` · `e: total = 10`
6. **Final answer**: So the shortest distances from A are A 0, B 4, C 2, D 5, and E 10. The shortest path to E is A → C → E, because 2 plus 8 equals 10.
   - board: `2+8=10`
   - sketch: `flowchart LR ; A[Start A=0] --> B[Pick smallest] ; B --> C[Finalize node] ; C --> D[Relax edges] ; D --> E{E finalized?} ; E -->\|no\| B ; E -->\|yes\| F[Stop: dist 10]`

## cs_dijkstra_a_to_e, run 2

Question: "Use Dijkstra's algorithm starting at A: what are the shortest distances to the other nodes, and what is the shortest path from A to E?" (cs_dijkstra_a_to_e.png)
Score 5/5 (b_stays_4 PASS, d_is_5 PASS, e_is_10 PASS, path_a_c_e PASS, via_d_is_12 PASS). Lesson 20.633 s, 6 steps, model gpt-5.5.

**Dijkstra from A to E**: We run Dijkstra’s algorithm on this weighted graph starting at A. The final shortest distances are A=0, B=4, C=2, D=5, E=10, and the shortest path to E is A → C → E.

1. **Set up the starting distances**: We’ll answer by running Dijkstra from A: start A at 0, and every other node at infinity until an edge improves it.
   - board: `a: A = 0` · `b+c+d+e: others = ∞`
2. **Iteration 1: finalize A**: Smallest tentative distance is A at 0, so A is finalized. Relax A’s edges: B becomes 4 through the 4-edge, and C becomes 2 through the 2-edge.
   - board: `a: ✓ done` · `b: B ∞→4` · `c: C ∞→2` · `a -> c: cost 2`
3. **Iteration 2: finalize C**: Now C has the smallest unvisited distance, 2, so C is finalized. Its edges give B no improvement, but D improves to 5 and E improves to 10.
   - board: `c: 2 ✓` · `b: stays 4` · `d: D ∞→5` · `e: E ∞→10`
4. **Iterations 3 and 4: check B, then D**: Next smallest is B at 4, so B is finalized; its route to D would be 14, not better than 5. Then D is finalized, and D to E would be 12, not better than 10.
   - board: `b: 4 ✓` · `d: stays 5` · `d: 5 ✓` · `e: stays 10`
5. **Iteration 5: finalize E and read the path**: Now E is the smallest unvisited node at 10, so E is finalized and we stop. Follow the predecessor trail: E came from C, and C came from A, so the shortest path is A to C to E.
   - board: `e: 10 ✓` · `a -> c: 2` · `c -> e: 8`
6. **Final answer**: So the shortest distances from A are A 0, B 4, C 2, D 5, and E 10. The shortest path from A to E is A → C → E, with total cost 2 + 8 = 10.
   - sketch: `flowchart LR ; A[A 0] --> C[C 2] ; C --> B[B 4] ; C --> D[D 5] ; C --> E[E 10] ; D --> E`

## cs_prim_mst, run 1

Question: "Using Prim's algorithm starting from A, which edges are added to the minimum spanning tree, in what order, and what is the total weight?" (cs_prim_mst.png)
Score 4/5 (edges_ad_df_ab PASS, edges_be_ce_eg PASS, prim_order PASS, total_39 PASS, skips_cycle_edges FAIL). Lesson 27.498 s, 7 steps, model gpt-5.5.

**Prim’s MST from A**: We run Prim’s algorithm directly on the graph, starting at A. Each step adds the cheapest edge from the growing tree to a new vertex; the final MST weight is 39.

1. **Start at A**: We’ll answer by growing one tree from A. I’m circling A as the start, then writing the first cheapest known connections: B costs 7 through A, and D costs 5 through A.
   - board: `B ∞→7 via A` · `d: D ∞→5 via A`
2. **Add A-D, then D-F**: Prim now picks the smallest outside connection, so A-D with weight 5 joins the tree. From D, F improves to 6 and E first appears at 15; next, D-F with weight 6 is the smallest, so F joins too.
   - board: `d: ✓ add D` · `F ∞→6 via D` · `e: E ∞→15 via D`
3. **Update through F**: Because F just entered, we check its outgoing edges. E gets cheaper, 15 to 8 through F, and G gets its first offer, 11 through F.
   - board: `✓ add F` · `e: E 15→8 via F` · `G ∞→11 via F`
4. **Add A-B, then improve E**: Among the outside offers, B at 7 is now cheapest, so A-B is added. Checking from B gives C an 8, and improves E again from 8 to 7 through B.
   - board: `✓ add B` · `C ∞→8 via B` · `e: E 8→7 via B`
5. **Add B-E, then improve C and G**: Now E also has cost 7, so Prim adds B-E. From E, C drops from 8 to 5, and G drops from 11 to 9.
   - board: `e: ✓ add E` · `C 8→5 via E` · `G 11→9 via E`
6. **Finish with C and G**: The next cheapest outside vertex is C at 5, so E-C joins; then only G remains, reached by E-G with cost 9. That completes the spanning tree.
   - board: `✓ add C` · `✓ add G`
7. **Answer and total**: So the Prim order from A is A-D, D-F, A-B, B-E, E-C, E-G. Add the weights: 5+6+7+7+5+9 = 39.
   - board: `total = 39`
   - sketch: `flowchart LR ; A[A] --> D[D] ; D --> F[F] ; A --> B[B] ; B --> E[E] ; E --> C[C] ; E --> G[G]`

Missing: skips_cycle_edges: MISSING any: 0 of 4 matched, need 1

## cs_prim_mst, run 2

Question: "Using Prim's algorithm starting from A, which edges are added to the minimum spanning tree, in what order, and what is the total weight?" (cs_prim_mst.png)
Score 4/5 (edges_ad_df_ab PASS, edges_be_ce_eg PASS, prim_order PASS, total_39 PASS, skips_cycle_edges FAIL). Lesson 24.605 s, 7 steps, model gpt-5.5.

**Prim’s Algorithm from A**: We’ll run Prim’s algorithm on this weighted graph, starting at A. The MST grows by repeatedly adding the cheapest edge that connects the current tree to one new vertex.

1. **Start at A**: We’re answering the MST question by growing one tree from A. I’ll circle A as the starting vertex, then write the first cheapest connections A offers to its neighbors.
   - board: `B ∞→7 via A` · `d: D ∞→5 via A` · `a: ✓ start`
2. **Add A-D**: Now the cheapest edge leaving the tree is A-D with weight 5, so D joins the tree. From D, we discover E at 15 and F at 6.
   - board: `d: ✓ add D` · `e: E ∞→15 via D` · `F ∞→6 via D`
3. **Add D-F**: Among the outside vertices, F has the smallest known connection, D-F with weight 6. Adding F improves E from 15 to 8 and discovers G at 11.
   - board: `✓ add F` · `e: E 15→8 via F` · `G ∞→11 via F`
4. **Add A-B**: Next the cheapest outside connection is B through A with weight 7. When B joins, C becomes 8 and E improves again from 8 to 7.
   - board: `✓ add B` · `C ∞→8 via B` · `e: E 8→7 via B`
5. **Add B-E, then E-C**: Now E is tied at 7 through B, so we add B-E. From E, C improves to 5 and G improves to 9; then E-C is the next cheapest edge.
   - board: `e: ✓ add E` · `C 8→5 via E` · `G 11→9 via E`
6. **Finish with E-G**: E-C with weight 5 adds C, and no cheaper updates appear. The last outside vertex is G, so E-G with weight 9 finishes the tree.
   - board: `✓ add C` · `✓ add G`
7. **Result**: So the MST edges, in order, are A-D, D-F, A-B, B-E, E-C, and E-G. Their weights add to 5+6+7+7+5+9 = 39.
   - sketch: `flowchart LR ; A[A start] --> D[add D] ; D --> F[add F] ; F --> B[add B] ; B --> E[add E] ; E --> C[add C] ; C --> G[add G]`

Missing: skips_cycle_edges: MISSING any: 0 of 4 matched, need 1

## math_derivative_tangent, run 1

Question: "The curve is f(x) = x² and the tangent touches it at a = 1. How do I find the tangent line y = mx + b?" (math_derivative_tangent.png)
Score 5/5 (point PASS, derivative PASS, slope PASS, intercept PASS, equation PASS). Lesson 17.347 s, 5 steps, model gpt-5.5.

**Tangent Line at a = 1**: We use the derivative to get the tangent slope, then plug the touch point into y = mx + b to find b. For f(x)=x² at a=1, the tangent line is y = 2x - 1.

1. **Where the tangent line comes from**: Great question — this page is showing the red curve y=f(x) and the purple tangent line at the point a,f(a). We’ll turn f(x)=x² and a=1 into that line equation.
2. **Find the point of tangency**: First compute the point: a=1, so f(1)=1²=1. That means the tangent touches the curve at (1,1), the little circled point on the graph.
   - board: `a=1, f(a)=1` · `(1,1)` · `touches here`
3. **Use the derivative for slope**: Now the slope m is not guessed from the picture; the formula says m=f′(a). For f(x)=x², f′(x)=2x, so at a=1 the slope is m=2.
   - board: `f′(x)=2x` · `m=2`
4. **Solve for b using the point**: Put m=2 and the point (1,1) into y=mx+b. So 1=2·1+b, which gives b=-1.
   - board: `1=2·1+b` · `b=-1`
5. **Final tangent line**: So the tangent line is y=2x−1. It has slope 2 and passes through (1,1), matching the purple line drawn on the page.
   - board: `y=2x−1` · `the tangent`
   - sketch: `flowchart TD ; A[f(x)=x²] --> B[find f(1)] ; B --> C[point (1,1)] ; A --> D[find f′(x)] ; D --> E[slope m=2] ; C --> F[solve b] ; E --> F`

## math_derivative_tangent, run 2

Question: "The curve is f(x) = x² and the tangent touches it at a = 1. How do I find the tangent line y = mx + b?" (math_derivative_tangent.png)
Score 5/5 (point PASS, derivative PASS, slope PASS, intercept PASS, equation PASS). Lesson 14.358 s, 5 steps, model gpt-5.5.

**Tangent Line to x² at a=1**: We find the tangent line by using the derivative for the slope at the touch point, then using the point (1,1) to solve for b. For f(x)=x² at a=1, the tangent line is y=2x−1.

1. **Find where the tangent lives**: This page is about the purple tangent line touching the red curve at a single point. Since you said a=1 for f(x)=x², I’ll circle the touch point where the answer starts.
2. **Compute the point**: For the curve f(x)=x², plug in a=1 to get the y-value. So the circled point is not mysterious: it is (1,1).
   - board: `(1,1)`
3. **Use derivative for slope**: The page tells us the tangent slope is m=f′(a). For f(x)=x², the derivative is f′(x)=2x, so at a=1 the slope is m=2.
   - board: `m=2`
4. **Solve for b**: Now use y=mx+b with the point (1,1) and slope 2. Substitute: 1=2·1+b, so b=-1.
   - board: `1=2·1+b` · `b=-1`
5. **Write the tangent line**: So the tangent line is y=2x−1. Follow the arrow: derivative gives the slope, the point gives b, and together they make the purple line.
   - board: `slope 2` · `y=2x−1`
   - sketch: `flowchart LR ; A[choose a=1] --> B[find point] ; B --> C[derivative slope] ; C --> D[solve b] ; D --> E[tangent line]`

## math_pythagoras, run 1

Question: "How does this picture prove the Pythagorean theorem?" (math_pythagoras_squares.jpg)
Score 5/5 (areas PASS, sides_3_4_5 PASS, sum_9_16_25 PASS, theorem PASS, rearrangement PASS). Lesson 22.134 s, 6 steps, model gpt-5.5.

**Pythagoras by Rearranging Squares**: The picture proves the Pythagorean theorem by showing that the two leg-squares can be rearranged to exactly fill the square on the hypotenuse. The matching angles make the tilted square line up with the triangle’s sides.

1. **Orient: three squares on one right triangle**: This picture proves Pythagoras by comparing the square on each side of the pale green right triangle. I’ll circle the triangle first: its sides are the two legs and the slanted hypotenuse.
   - board: `side c`
2. **The left red square is one leg squared**: The red square on the left sits on one leg of the triangle, so its area represents one leg squared. Think of its 4 by 4 grid as a concrete area: 16 little squares.
   - board: `built on leg` · `4² = 16`
3. **The bottom yellow square is the other leg squared**: Now the yellow square underneath is built on the other leg. Its 3 by 3 grid gives the second area: 9 little squares.
   - board: `built on leg` · `3² = 9`
4. **The tilted square is the hypotenuse squared**: The tilted square is built on the slanted side, the hypotenuse. Inside it, the red and yellow pieces together make a 5 by 5 square: 25 little squares.
   - board: `side c square` · `5² = 25`
5. **Why the pieces fit**: The angle marks explain the fit: α and β are the sharp angles of the same right triangle. Their sum is 90°, so copies of the leg-squares can turn and line up along the hypotenuse square.
   - board: `α + β = 90°`
6. **The proof in one equation**: So the two leg areas combine to equal the hypotenuse area. Here that is 16 plus 9 equals 25, which is exactly a² + b² = c².
   - board: `same red area` · `same yellow area` · `16 + 9 = 25`
   - sketch: `flowchart LR ; A[leg square a²] --> C[combine areas] ; B[leg square b²] --> C ; C --> D[hypotenuse square c²] ; D --> E[a² + b² = c²]`

## math_pythagoras, run 2

Question: "How does this picture prove the Pythagorean theorem?" (math_pythagoras_squares.jpg)
Score 5/5 (areas PASS, sides_3_4_5 PASS, sum_9_16_25 PASS, theorem PASS, rearrangement PASS). Lesson 19.874 s, 5 steps, model gpt-5.5.

**Pythagoras by Rearranging Squares**: This picture proves the Pythagorean theorem by using the same right triangle three ways: the squares on the two legs exactly fill the square on the hypotenuse. The key is that the colored little grid-squares are area pieces, not just decoration.

1. **Find the right triangle**: This picture proves Pythagoras by building squares on the three sides of this pale right triangle. I’ll circle the triangle first, because every colored block is tied to one of its sides.
   - board: `90° corner`
2. **Name the three side-squares**: The red square sits on one leg, the yellow square sits on the other leg, and the tilted red-plus-yellow square sits on the hypotenuse. So the theorem is an area statement about these three squares.
   - board: `area = c²`
3. **Count the leg areas**: Now count grid-squares: the left square is 4 by 4, so its area is 16. The bottom square is 3 by 3, so its area is 9.
   - board: `4×4 = 16` · `3×3 = 9` · `add areas`
4. **See the same pieces on the hypotenuse**: Look at the tilted square: its inside is made from exactly those 16 red pieces plus 9 yellow pieces. Nothing is stretched; the pieces are just rearranged along the slanted side.
   - board: `16 + 9 = 25`
5. **State the proof**: So the square on the hypotenuse has the same area as the two leg-squares together. That is the Pythagorean theorem: a² plus b² equals c².
   - board: `a² part` · `b² part` · `a²+b²=c²`
   - sketch: `flowchart LR ; A[Right triangle] --> B[Build leg squares] ; B --> C[Add their areas] ; C --> D[Rearrange pieces] ; D --> E[Hypotenuse square] ; E --> F[a²+b²=c²]`

## math_quadratic, run 1

Question: "Where does this parabola cross the x-axis? Solve its equation step by step." (math_quadratic_roots.png)
Score 5/5 (set_zero PASS, method PASS, root_2 PASS, root_minus_1 PASS, graph_link PASS). Lesson 19.205 s, 5 steps, model gpt-5.5.

**Finding the x-intercepts**: We’ll answer where the red parabola crosses the x-axis by solving its equation y = x² − x − 2. The crossings happen when y is set to 0, giving the roots x = −1 and x = 2.

1. **Orient: crossings mean y = 0**: Great question! The x-axis crossings are exactly where the red curve hits y = 0, so we’ll use the printed equation and set it equal to zero.
2. **Set the equation to zero**: At an x-axis crossing, the height y is zero. So I replace y with 0, giving 0 = x² − x − 2.
   - board: `set y=0` · `0 = x²−x−2`
3. **Factor the quadratic**: Now factor x² − x − 2. We need two numbers that multiply to −2 and add to −1: those are −2 and +1.
   - board: `−2·1=−2` · `−2+1=−1`
4. **Use the zero product rule**: So the equation becomes 0 = (x − 2)(x + 1). A product is zero only when one factor is zero, so x = 2 or x = −1.
   - board: `0=(x−2)(x+1)` · `x=2` · `x=−1`
5. **Mark the two crossings**: Here are the two x-axis crossings on the graph: one at −1 and one at 2. So the parabola crosses at (−1, 0) and (2, 0).
   - board: `roots: −1, 2`
   - sketch: `flowchart LR ; A[Set y=0] --> B[Factor quadratic] ; B --> C[Zero product] ; C --> D[x=-1] ; C --> E[x=2] ; D --> F[Plot crossings] ; E --> F`

## math_quadratic, run 2

Question: "Where does this parabola cross the x-axis? Solve its equation step by step." (math_quadratic_roots.png)
Score 5/5 (set_zero PASS, method PASS, root_2 PASS, root_minus_1 PASS, graph_link PASS). Lesson 24.229 s, 5 steps, model gpt-5.5.

**Finding the x-intercepts**: We solve where the parabola crosses the x-axis by setting y = 0, then factoring the quadratic. The graph and the algebra agree: the crossings are x = -1 and x = 2.

1. **Where the answer lives**: We’re finding where this parabola crosses the x-axis. I’ll circle the equation and the two red crossings, because x-intercepts happen exactly where y equals zero.
2. **Set y equal to zero**: At an x-axis crossing, the height is zero, so replace y with 0. That turns the graph question into the equation 0 = x² - x - 2.
   - board: `0 = x² - x -`
3. **Factor the quadratic**: Now factor x² - x - 2. We need two numbers that multiply to -2 and add to -1: those are -2 and +1.
   - board: `(x - 2)(x + 1)`
4. **Use the zero-product rule**: If two factors multiply to zero, one factor must be zero. So x - 2 = 0 gives x = 2, and x + 1 = 0 gives x = -1.
   - board: `x = 2` · `x = -1`
5. **Match algebra to the graph**: Here’s the full path: set y to zero, factor, then solve each factor. The parabola crosses the x-axis at (-1, 0) and (2, 0).
   - board: `two intercepts`
   - sketch: `flowchart LR ; A[Set y = 0] --> B[Factor quadratic] ; B --> C[Set factors zero] ; C --> D[x = -1] ; C --> E[x = 2]`

## math_unit_circle, run 1

Question: "What is sin(150°) and why?" (math_unit_circle.png)
Score 5/5 (value_half PASS, y_coordinate PASS, point_150 PASS, reference_30 PASS, quadrant_sign PASS). Lesson 18.495 s, 6 steps, model gpt-5.5.

**Why sin(150°) = 1/2**: On the unit circle, sine is the y-coordinate of the point at an angle. Since 150° has the same reference angle as 30° and lies in Quadrant II, its sine is positive 1/2.

1. **Find 150° on the unit circle**: We’re answering: what is sin(150°)? I’ll circle 150° first, because sine comes from the point on the unit circle at that angle.
   - board: `angle location`
2. **Sine means the y-coordinate**: On this circle, each angle lands on an ordered pair. The sine is the vertical coordinate, so we only need the second number of the 150° point.
   - board: `lands here` · `sin = y`
3. **Read the coordinate at 150°**: Now look just outside that blue point: the coordinate shown is (-√3/2, 1/2). Since sine is y, grab the 1/2 part.
   - board: `the y-value`
4. **Why it is positive**: 150° sits in Quadrant II, above the x-axis. Above the x-axis means y is positive, so the sine value is positive.
   - board: `above = +y` · `positive sine`
5. **Connect to the 30° reference angle**: The reason it matches 1/2 is that 150° is 30° away from 180°. That reference angle has the same height as 30° on the right side.
   - board: `30° back` · `same height`
6. **Final answer**: So the answer is sin(150°) = 1/2. We use the y-coordinate at 150°, and it is positive because the point is above the x-axis.
   - board: `sin150° = 1/2`
   - sketch: `flowchart LR ; A[Find 150°] --> B[Read point] ; B --> C[Take y-coordinate] ; C --> D[Above x-axis] ; D --> E[Positive 1/2]`

## math_unit_circle, run 2

Question: "What is sin(150°) and why?" (math_unit_circle.png)
Score 5/5 (value_half PASS, y_coordinate PASS, point_150 PASS, reference_30 PASS, quadrant_sign PASS). Lesson 16.352 s, 5 steps, model gpt-5.5.

**Why sin(150°) = 1/2**: The unit circle shows sine as the y-coordinate of a point. At 150°, the point is in Quadrant II, where the reference angle is 30°, so its height is the same as sin(30°): 1/2.

1. **Find 150° on the unit circle**: We’re answering: what is sin(150°)? I’ll circle 150° first, because sine comes from the height of that point on the unit circle.
   - board: `QII angle`
2. **Sine means height**: On this page, each outer ordered pair is the point on the unit circle. Sine is the y-coordinate, so we want the second number next to 150°.
   - board: `sin = y` · `look outward`
3. **Read the y-coordinate**: The coordinate beside 150° is negative x, positive y: (-√3/2, 1/2). So the sine value is the height, 1/2.
   - board: `height = 1/2`
4. **Why it matches 30°**: Here’s the why: 150° is 30° away from the negative x-axis, making a 30° reference angle. A 30° reference angle has height 1/2, and Quadrant II keeps y positive.
   - board: `same height` · `y stays +`
5. **Final answer**: So sin(150°) = 1/2. The angle lands in Quadrant II, and sine is the positive y-coordinate of that unit-circle point.
   - board: `sin150° = 1/2`

## cs_gbn_vs_sr, run 1

Question: "In both timelines frame 2 is damaged. What does the receiver do with the frames that arrive after it, and which frames does the sender retransmit, in (a) Go-Back-N versus (b) Selective Repeat?" (cs_gbn_vs_sr.png)
Score 4/5 (gbn_discards_3_to_8 PASS, gbn_timeout_resends_from_2 PASS, sr_buffers_3_to_5 PASS, sr_nak_only_2 PASS, sr_ack_5 FAIL). Lesson 22.576 s, 7 steps, model gpt-5.5.

**Damaged Frame 2: Go-Back-N vs Selective Repeat**: The page compares what happens after frame 2 is damaged in two sliding-window protocols. In Go-Back-N, the receiver discards later out-of-order frames and the sender resends from 2 onward; in Selective Repeat, the receiver buffers later frames and the sender resends only the missing damaged frame 2.

1. **Find the two stories**: This page answers your question by showing the same damage in two protocols: top is Go-Back-N, bottom is Selective Repeat. I’ll circle the two outcomes we care about after frame 2 breaks.
2. **In Go-Back-N, frame 2 fails**: In the top timeline, frame 2 is the first bad one, marked by the error and the missing normal ACK. Because Go-Back-N accepts only the next expected frame, the receiver keeps waiting for 2.
   - board: `missing 2`
3. **Go-Back-N discards after 2**: Now follow the solid arrivals after the damaged 2: frames 3, 4, 5, 6, 7, and 8 reach the receiver, but they are out of order. So the data link layer discards them, exactly where I’m boxing the D’s.
   - board: `? -> d: out of order` · `throw away 3–8`
4. **Go-Back-N retransmits the run**: After the timeout interval expires, the sender goes back to the damaged frame 2. That is why the top row restarts with 2, 3, 4, 5, 6, 7, 8, and then 9.
   - board: `resend 2–8`
5. **Selective Repeat buffers after 2**: In the bottom timeline, frame 2 is also damaged, but Selective Repeat can keep later correct frames. So 3, 4, and 5 are buffered while the receiver still waits for only frame 2.
   - board: `save 3–5`
6. **Selective Repeat retransmits only 2**: The NAK points to exactly what is missing: frame 2. So the sender retransmits only 2, then continues with new frames like 6, 7, 8, and onward.
   - board: `resend only 2`
7. **Answer in one picture**: Here’s the big contrast: Go-Back-N throws away later arrivals and resends the whole run from 2; Selective Repeat stores later arrivals and resends just 2. That is the answer to your question.
   - board: `key difference`
   - sketch: `flowchart TD ; A[Frame 2 damaged] ; B{Protocol?} ; C[Go-Back-N] ; D[Discard later] ; E[Resend 2 onward] ; F[Selective Repeat] ; G[Buffer later] ; H[Resend only 2] ; A --> B ; B --> C ; C --> D ; D --> E ; B --> F ; F --> G ; G --> H`

Missing: sr_ack_5: MISSING any: 0 of 5 matched, need 1

## cs_gbn_vs_sr, run 2

Question: "In both timelines frame 2 is damaged. What does the receiver do with the frames that arrive after it, and which frames does the sender retransmit, in (a) Go-Back-N versus (b) Selective Repeat?" (cs_gbn_vs_sr.png)
Score 3/5 (gbn_discards_3_to_8 FAIL, gbn_timeout_resends_from_2 PASS, sr_buffers_3_to_5 PASS, sr_nak_only_2 PASS, sr_ack_5 FAIL). Lesson 20.226 s, 6 steps, model gpt-5.5.

**Damaged Frame 2: Go-Back-N vs Selective Repeat**: The page compares what happens after frame 2 is damaged in two sliding-window protocols. In Go-Back-N the receiver discards later out-of-order frames, while in Selective Repeat it buffers them and asks only for the missing frame.

1. **Orient: both timelines start with frame 2 damaged**: Great question: both diagrams show frame 2 getting damaged, but the receiver reacts differently. I’ll circle the two protocol outcomes: discarded above, buffered below.
2. **In (a), damaged frame 2 creates a gap**: In Go-Back-N, the receiver is waiting for frame 2 next. When frame 2 has an error, every later arrival is out of order, so the receiver marks them D for discarded.
   - board: `d: out of order`
3. **Go-Back-N sender retransmits from 2 onward**: Now follow the timeout interval: because ACK 2 never arrives, the sender times out. Go-Back-N retransmits frame 2 and then goes back through the whole outstanding run: 2, 3, 4, 5, 6, 7, 8.
   - board: `timeout fires`
4. **In (b), receiver buffers later correct frames**: Selective Repeat is pickier and smarter. Frame 2 is still damaged, but frames 3, 4, and 5 are kept in the receiver buffer instead of being thrown away.
   - board: `saved for later`
5. **Selective Repeat retransmits only the missing frame**: Look at the NAK 2 in the lower timeline: it asks specifically for frame 2. So the sender retransmits only frame 2, then normal sending continues with 6, 7, 8 and beyond.
   - board: `resend 2`
6. **Answer recap**: So the answer is: Go-Back-N discards frames after damaged 2 and retransmits 2 through 8. Selective Repeat buffers frames after damaged 2 and retransmits only 2.
   - board: `d -> ?: key difference`
   - sketch: `flowchart TD ; A[Frame 2 damaged] --> B{Protocol?} ; B --> C[Go-Back-N] ; C --> D[Discard later] ; C --> E[Resend 2-8] ; B --> F[Selective Repeat] ; F --> G[Buffer later] ; F --> H[Resend 2]`

Missing: gbn_discards_3_to_8: MISSING any: 0 of 6 matched, need 1; sr_ack_5: MISSING any: 0 of 5 matched, need 1

## cs_tcp_handshake, run 1

Question: "Walk me through this TCP three-way handshake: what do the SYN, Seq and Ack values in each of the three segments mean, and why is the first acknowledgement number 1024?" (cs_tcp_handshake.png)
Score 5/5 (client_syn_1023 PASS, server_isn_2131691 PASS, ack_1024_is_1023_plus_1 PASS, final_ack_2131692 PASS, third_seq_1024_established PASS). Lesson 20.616 s, 6 steps, model gpt-5.5.

**TCP Three-Way Handshake Numbers**: This diagram shows TCP’s three-step connection setup between Client A and Server B. The key idea: SYN consumes one sequence number, so the peer acknowledges the next number it expects.

1. **Orient: three messages over time**: This page is the TCP three-way handshake: Client A and Server B trade three segments as time flows downward. We’ll track SYN, Seq, and Ack on each slanted message.
   - board: `later`
2. **client opens with SYN**: First, the client sends SYN=1 with Seq 1023 and ACK=0. SYN means “start a connection,” Seq 1023 is the client’s initial sequence number, and ACK=0 means no server bytes are being acknowledged yet.
   - board: `client ISN`
3. **server replies and acknowledges**: Second, the server answers with its own SYN=1, its own Seq 2131691, and ACK=1. The Ack Number is 1024 because the client’s SYN used sequence 1023, so the next expected client number is 1023 plus 1.
   - board: `1023 + SYN`
4. **Why 1024 exactly?**: Here’s the accounting: a SYN flag consumes one sequence number even when it carries no data. So the server’s arrow points back to the client saying, “I got 1023; send me 1024 next.”
   - board: `+1 for SYN` · `next expected`
5. **client finishes the handshake**: Third, the client sends SYN=0, Seq=1024, ACK=1, and Ack Number 2131692. That final Ack Number is the same rule: server Seq 2131691 plus one for the server’s SYN.
   - board: `2131691 + 1`
6. **Recap: SYNs create the +1 acknowledgements**: So the answer is: each side chooses its own Seq, and each Ack Number names the next sequence number expected from the other side. The first acknowledgement is 1024 because Client A’s SYN at Seq 1023 counts as one sequence number.
   - board: `next = 1024`
   - sketch: `flowchart TD ; A[Client SYN 1023] --> B[Server ACK 1024] ; B --> C[Server SYN 2131691] ; C --> D[Client ACK 2131692] ; D --> E[Connection open]`

## cs_tcp_handshake, run 2

Question: "Walk me through this TCP three-way handshake: what do the SYN, Seq and Ack values in each of the three segments mean, and why is the first acknowledgement number 1024?" (cs_tcp_handshake.png)
Score 5/5 (client_syn_1023 PASS, server_isn_2131691 PASS, ack_1024_is_1023_plus_1 PASS, final_ack_2131692 PASS, third_seq_1024_established PASS). Lesson 17.151 s, 6 steps, model gpt-5.5.

**TCP Three-Way Handshake Values**: This diagram shows TCP connection setup between Client A and Server B. The key rule is: a SYN consumes one sequence number, so the next expected byte is Seq + 1, which explains Ack Number = 1024.

1. **Orient: three messages over time**: We’re walking down the time arrow through the TCP three-way handshake. I’ll use blue for Client A, green for Server B, and orange for the sequence-number rule that answers why 1024 appears.
2. **Segment 1: client opens with SYN**: First, the client sends a SYN segment to say, “I want to start a connection.” Its Seq is 1023, the client’s initial sequence number; ACK is 0 because the client has not received anything from B yet.
   - board: `open request` · `client ISN`
3. **Segment 2: server replies and acknowledges**: Now the server replies with SYN=1 and ACK=1: it is both opening its side and acknowledging the client’s SYN. The acknowledgement number is 1024 because TCP says a SYN uses one sequence number: 1023 plus 1.
   - board: `1023+1=1024`
4. **Segment 2 also gives server’s Seq**: The same green segment has the server’s own Seq, 2131691. That is B’s initial sequence number, so the next client ACK must point to 2131692.
   - board: `server ISN` · `2131691+1`
5. **Segment 3: client finishes the handshake**: Finally, the client sends ACK=1 with Seq=1024 and Ack Number=2131692. SYN=0 now because this is no longer a setup request; it can carry data after the connection is established.
6. **Recap: what each value means**: So the answer is: SYN starts each side, Seq names that side’s starting number, and Ack says the next number expected from the other side. The first acknowledgement is 1024 exactly because A’s SYN at Seq 1023 consumes one sequence number.
   - board: `SYN consumes 1`
   - sketch: `flowchart TD ; A[A SYN Seq 1023] --> B[B SYN ACK] ; B --> C[Ack 1024] ; C --> D[A ACK] ; D --> E[Ack 2131692] ; E --> F[Connection open]`

## cs_deadlock_rag, run 1

Question: "Is there a deadlock in this resource-allocation graph? R3 has two instances, so does the cycle really mean deadlock?" (cs_deadlock_rag.png)
Score 1/5 (p1_holds_r3_waits_r1 FAIL, p2_holds_r1_waits_r2 PASS, p3_holds_r2_waits_r3 FAIL, cycle FAIL, deadlock_because_no_free_instance FAIL). Lesson 18.163 s, 5 steps, model gpt-5.5.

**Deadlock with Two R3 Instances**: This resource-allocation graph has a cycle, but because R3 has two instances, the cycle alone does not prove deadlock. We test it by simulating who can finish and release resources.

1. **Orient: what the arrows mean**: We’re checking whether this resource-allocation graph is truly deadlocked. I’ll circle the resource boxes and the process circles, because arrows into processes mean allocations, and arrows into resources mean requests.
   - board: `request vs allocation`
2. **Count the R3 instances**: Your key worry is right here: R3 has two dots, so it has two instances. One instance is allocated to P1, and the other is allocated to P2.
   - board: `allocated`
3. **Follow the requests in the cycle**: Now follow the waiting chain: P1 is requesting R1, R1 is held by P2, and P2 is requesting R2. That creates a cycle-looking dependency, but we still must ask whether any process can escape.
   - board: `requests` · `allocated` · `requests`
4. **Find who can finish first**: Here is the important escape: P3 holds no resource needed by others in that cycle, and it is only requesting R3. When P1 or P2 later releases an R3 instance, P3 can get one and finish too.
   - board: `requests` · `2 total, 0 free`
5. **Answer: cycle does not force deadlock**: So the answer is: the cycle is necessary-looking, but not sufficient when a resource has multiple instances. Because R3 has two instances, this graph’s cycle alone does not prove deadlock; you must check whether all processes are permanently waiting.
   - board: `cycle ≠ deadlock`
   - sketch: `flowchart TD ; A[See cycle] --> B[Count instances] ; B --> C{Multiple?} ; C -->\|yes\| D[Test finish] ; C -->\|no\| E[Deadlock possible] ; D --> F[Not proven]`

Missing: p1_holds_r3_waits_r1: MISSING all[1] \| p1 is requesting r1, r1; p3_holds_r2_waits_r3: MISSING all[1] \| MISSING all[2]; cycle: cycl \| MISSING any: 0 of 13 matched, need 1; deadlock_because_no_free_instance: deadlocked \| MISSING any: 0 of 6 matched, need 1

## cs_deadlock_rag, run 2

Question: "Is there a deadlock in this resource-allocation graph? R3 has two instances, so does the cycle really mean deadlock?" (cs_deadlock_rag.png)
Score 4/5 (p1_holds_r3_waits_r1 PASS, p2_holds_r1_waits_r2 PASS, p3_holds_r2_waits_r3 PASS, cycle FAIL, deadlock_because_no_free_instance PASS). Lesson 14.852 s, 5 steps, model gpt-5.5.

**Deadlock with Multi-Instance R3**: We’ll read the resource-allocation graph by following assignment and request arrows, then test the cycle carefully. Because R3 has two instances, a cycle is suspicious but not automatically a deadlock.

1. **Orient: what the graph means**: This is a resource-allocation graph: green boxes are resource types, orange circles are processes. To answer your question, I’ll circle the two-instance resource R3 first.
2. **Read the arrow directions**: Now follow arrowheads: resource-to-process means an instance is already assigned; process-to-resource means the process is waiting. So R3 is currently giving one instance to P1 and one to P2.
   - board: `assigned` · `assigned` · `0 free now`
3. **Find the waiting cycle**: Here is the tempting cycle: P1 waits for R1, R1 is assigned to P2, P2 waits for R2, and R2 is assigned to P3. Then P3 requests R3, closing the loop toward holders P1 and P2.
   - board: `waits` · `held by` · `waits`
4. **Why R3’s two instances matter**: The key check is availability, not just a cycle. Because both R3 dots are already assigned, P3’s request for R3 cannot be satisfied right now.
   - board: `requests`
5. **Final answer**: So yes, this graph is deadlocked: every process in the cycle is waiting, and no R3 instance is free to rescue P3. With multiple instances, a cycle is not always deadlock—but here both R3 instances are occupied.
   - board: `cycle + no free`
   - sketch: `flowchart LR ; A[Find cycle] --> B[Check instances] ; B --> C[Any free?] ; C -->\|yes\| D[Not certain] ; C -->\|no\| E[Deadlock]`

Missing: cycle: cycl \| MISSING any: 0 of 13 matched, need 1

## cs_lru_cache, run 1

Question: "This LRU example has 4 slots and the access sequence A B C D E D F (the number in brackets is the time of last use). Why does E replace A, why does F replace B, and how many hits and misses are there?" (cs_lru_cache.png)
Score 5/5 (e_evicts_a PASS, d_hit_updated PASS, f_evicts_b PASS, six_misses PASS, one_hit PASS). Lesson 20.772 s, 6 steps, model gpt-5.5.

**LRU: Why E Evicts A and F Evicts B**: We simulate the reference string A B C D E D F with 4 frames. LRU evicts the page whose bracketed time is smallest—the page used longest ago.

1. **Set up the rule**: This page is an LRU replacement trace for A B C D E D F. I’ll circle the moment memory first becomes full, because after that every miss must choose the least-recently-used page.
   - board: `4 slots full`
2. **First four references fill free slots**: For A, B, C, and D, each page is missing, but there is still an empty slot. So these are four misses, and no eviction happens yet.
   - board: `miss: free slot` · `miss` · `miss` · `miss → full`
3. **E replaces A**: Now E is referenced at time 4, and it is not in memory, so this is a miss. Among A(0), B(1), C(2), and D(3), A has the oldest last-use time, so E replaces A.
   - board: `evicts oldest` · `miss #5`
4. **D is a hit, time updates**: Next D is referenced again at time 5. It is already in a frame, so it is the only hit, and D’s last-use time updates from 3 to 5.
   - board: `3→5` · `hit #1`
5. **F replaces B**: Finally F is referenced at time 6, and it is missing. Now the stored times are E(4), B(1), C(2), D(5), so B is the least recently used and F replaces B.
   - board: `evicts oldest` · `miss #6`
6. **Final answer**: So E replaces A because A’s last-use time 0 is oldest; F replaces B because B’s last-use time 1 is oldest then. The count is 6 misses and 1 hit.
   - board: `6 misses, 1 hit`
   - sketch: `flowchart LR ; A[Reference page] --> B{In frame?} ; B -->\|yes\| C[Hit: update time] ; B -->\|no\| D{Free slot?} ; D -->\|yes\| E[Load page] ; D -->\|no\| F[Evict oldest] ; F --> E`

## cs_lru_cache, run 2

Question: "This LRU example has 4 slots and the access sequence A B C D E D F (the number in brackets is the time of last use). Why does E replace A, why does F replace B, and how many hits and misses are there?" (cs_lru_cache.png)
Score 5/5 (e_evicts_a PASS, d_hit_updated PASS, f_evicts_b PASS, six_misses PASS, one_hit PASS). Lesson 20.037 s, 6 steps, model gpt-5.5.

**LRU: Why E Evicts A and F Evicts B**: This page simulates LRU page replacement with 4 frames for the reference string A B C D E D F. LRU evicts the page with the oldest last-use time, giving 6 misses and 1 hit.

1. **Orient: four frames, oldest loses**: We’re answering why E kicks out A and F kicks out B. This is LRU: when all 4 slots are full, replace the page whose bracket time is smallest—the oldest last use.
   - board: `full: choose oldest`
2. **Load A, B, C, D: four misses**: First we just fill free slots: A, then B, then C, then D are all not present. So each is a miss, but no eviction happens yet.
   - board: `miss; free slot` · `miss; free slot` · `miss; free slot` · `miss; free slot`
3. **At E, compare last-use times**: Now E arrives when memory is full, so LRU compares A(0), B(1), C(2), D(3). The smallest time is A(0), so E replaces A.
   - board: `evicted by E` · `miss; A out`
4. **At D, it is a hit**: Next the reference is D. D is already in the frames, so this is the only hit; its last-use time updates from 3 to 5.
   - board: `hit: 3→5`
5. **At F, B is now oldest**: Finally F arrives and is not present, so another miss. Among E(4), B(1), C(2), D(5), B has the smallest last-use time, so F replaces B.
   - board: `evicted by F` · `miss; B out`
6. **Answer: 6 misses, 1 hit**: So the answer is: E replaces A because A was last used at time 0; F replaces B because B was last used at time 1. Total: 6 misses and 1 hit.
   - board: `6 misses, 1 hit`
   - sketch: `flowchart LR ; A[Reference page] --> B{In frames?} ; B -->\|yes\| C[Hit: update time] ; B -->\|no\| D{Free slot?} ; D -->\|yes\| E[Load page] ; D -->\|no\| F[Evict oldest] ; F --> E`

## cs_sjf_gantt, run 1

Question: "This chart shows non-preemptive Shortest Job First. Why do P9, P8 and P7 run in that order, why does P12 wait so long, and what is the average waiting time?" (cs_sjf_gantt.png)
Score 5/5 (order_p9_p8_p7 PASS, waits_p7_p8_p9 PASS, p12_waits_8 PASS, total_33 PASS, average_2_36 PASS). Lesson 29.719 s, 8 steps, model gpt-5.5.

**Non-Preemptive SJF: Why This Order?**: This chart is a non-preemptive Shortest Job First schedule: whenever the CPU becomes free, it chooses the ready process with the smallest burst time and runs it to completion. The key answers are: P9 then P8 then P7 because their bursts are 1, 2, 3; P12 waits until 21 because shorter ready jobs keep beating it; average waiting time is 33/14 = 2.36.

1. **Orient: read the schedule rule**: This page is a non-preemptive SJF timeline: gray means waiting, black means running. We’ll answer your question by following each CPU choice, especially the P9-P8-P7 group and P12’s long wait.
2. **First ready batch: ties go by listing order**: At t=0, P1, P2, and P3 are all ready with burst 1. Since they tie, listing order picks P1, then P2, then P3; their waits become 0, 1, and 2.
   - board: `P1 wait 0` · `P2 wait 1` · `P3 wait 2`
3. **At t=3: choose 1, then 2, then 3**: At t=3, P4, P5, and P6 arrive together. SJF picks the shortest burst first: P4 runs 3-4, then P5 4-6, then P6 6-9.
   - board: `P4 wait 0` · `P5 wait 1` · `P6 wait 3`
4. **Why P9, P8, then P7?**: Now your main question: at t=9, P7, P8, and P9 are all ready. Their bursts are 3, 2, and 1, so SJF chooses P9, then P8, then P7.
   - board: `burst 1 → first` · `burst 2 → next` · `burst 3 → last`
5. **Their actual waiting times**: Because P9 runs 9-10, P8 runs 10-12, and P7 runs 12-15. Waiting is start minus arrival, so their waits are 2, 3, and 5.
   - board: `P9 wait 2` · `P8 wait 3` · `P7 wait 5`
6. **Why P12 waits so long**: At t=15, P10, P11, and P12 are ready, but P12 has burst 3. P10 and P11 are shorter, then at t=18 the new P13 and P14 are also shorter, so P12 finally runs 21-24.
   - board: `shorter: wait 2` · `shorter: wait 3` · `P12 wait 8`
7. **Late arrivals still beat P12**: Notice the non-preemptive detail: P12 is waiting, not running, so new shorter jobs can still be chosen when the CPU frees up. P13 waits 1, P14 waits 2, and P12 waits until 21.
   - board: `P13 wait 1` · `P14 wait 2` · `delay P12`
8. **Final answer: average waiting time**: Add every wait: 0+1+2+0+1+3+5+3+2+2+3+8+1+2 = 33. Divide by 14 processes: the average waiting time is 33/14 = 2.36 time units.
   - board: `Avg wait = 2.36`
   - sketch: `flowchart LR ; A[CPU free] --> B[Find ready] ; B --> C[Pick shortest burst] ; C --> D[Run to finish] ; D --> E[Record wait] ; E --> A`

## cs_sjf_gantt, run 2

Question: "This chart shows non-preemptive Shortest Job First. Why do P9, P8 and P7 run in that order, why does P12 wait so long, and what is the average waiting time?" (cs_sjf_gantt.png)
Score 5/5 (order_p9_p8_p7 PASS, waits_p7_p8_p9 PASS, p12_waits_8 PASS, total_33 PASS, average_2_36 PASS). Lesson 35.973 s, 8 steps, model gpt-5.5.

**Non-preemptive SJF on this chart**: This Gantt-style chart shows non-preemptive Shortest Job First: whenever the CPU becomes free, choose the ready process with the smallest burst and run it to completion. That rule explains P9 → P8 → P7, why P12 is delayed, and gives an average waiting time of 33/14 = 2.36.

1. **Orient: shortest ready job wins**: This page is a non-preemptive SJF schedule: gray is waiting, black is running. We’ll answer your question by following each CPU-free moment, not by eyeballing the bars.
2. **First arrivals at time 0**: At time 0, P1, P2, and P3 are all ready with burst 1. The tie goes by listing order, so P1 runs first, then P2, then P3.
   - board: `P1 wait 0` · `P2 wait 1` · `P3 wait 2`
3. **Time 3 group: P4, P5, P6**: At time 3, the ready bursts are P4=1, P5=2, and P6=3. SJF picks them in increasing burst length: P4, then P5, then P6.
   - board: `P4 wait 0` · `P5 wait 1` · `P6 wait 3`
4. **Why P9, P8, P7 run in that order**: Here’s the key part: P7, P8, and P9 all arrive at 7, but the CPU is busy with P6 until 9. At 9, their bursts are 3, 2, and 1, so SJF runs P9, then P8, then P7.
   - board: `CPU frees` · `P9 wait 2` · `P8 wait 3`
5. **P7 finishes that trio**: After P9 and P8 finish, only P7 remains from the time-7 group. It finally runs 12 to 15, so its waiting time is 12 minus 7, which is 5.
   - board: `P7 wait 5` · `12−7=5`
6. **Why P12 waits so long**: Now look at P12: it arrives at 13, but at each choice point a shorter ready job exists. P10 and P11 go first, then new arrivals P13 and P14 are shorter than P12.
   - board: `P10 wait 2` · `P11 wait 3` · `P13 wait 1`
7. **P12 finally runs last**: At time 19, P14 is still shorter than P12, so P14 runs before it. Only at time 21 is P12 the only ready process, so P12 waits 21 minus 13: 8 units.
   - board: `P14 wait 2` · `P12 wait 8` · `21−13=8`
8. **Average waiting time**: So the answer is: P9, P8, P7 run by burst lengths 1, 2, 3; P12 waits because shorter jobs keep appearing. Adding all waits gives 33, and 33 divided by 14 is 2.36.
   - board: `33/14 = 2.36`
   - sketch: `flowchart LR ; A[CPU free] --> B[Find ready jobs] ; B --> C[Pick shortest burst] ; C --> D[Run to finish] ; D --> E[Record wait] ; E --> A`

## math_kinematics, run 1

Question: "For the example at the bottom, how far does the object travel in the 5 seconds? Check it with the v–t graph." (math_kinematics_slide.png)
Score 4/5 (formula FAIL, substitution PASS, final_velocity PASS, distance_25 PASS, graph_area PASS). Lesson 16.659 s, 5 steps, model gpt-5.5.

**Distance in 5 Seconds**: We use the constant-acceleration displacement formula and then check the same distance as the area under the velocity–time graph. For this example, the object travels 25 m.

1. **Find the asked example**: We’re answering: how far does the bottom example travel in 5 seconds? I’ll circle the example first, because it gives the starting velocity, acceleration, time, and final velocity.
2. **Choose the displacement equation**: Distance traveled here is displacement s. Since we know u, a, and t, the useful equation is s = ut plus one-half at squared.
   - board: `plug in` · `finds distance`
3. **Compute s from the formula**: Now substitute carefully: s = 0 times 5 plus one-half times 2 times 5 squared. That becomes 0 plus 25, so s = 25 meters.
   - board: `s=0·5+½·2·5²` · `s = 25 m`
4. **Check with the v–t graph**: The graph check uses area under the velocity–time line. Starting at 0 m/s and ending at 10 m/s over 5 s gives a triangle: one-half base times height.
   - board: `½·5·10=25 m`
5. **Answer and connection**: So the object travels 25 m in the 5 seconds. The formula and the shaded v–t area match because displacement is area under a velocity–time graph.
   - board: `same s` · `answer: 25 m`
   - sketch: `flowchart LR ; A[Read u,a,t] --> B[Use s formula] ; B --> C[Compute 25 m] ; C --> D[Check graph area] ; D --> E[Same 25 m]`

Missing: formula: MISSING any: 0 of 3 matched, need 1

## math_kinematics, run 2

Question: "For the example at the bottom, how far does the object travel in the 5 seconds? Check it with the v–t graph." (math_kinematics_slide.png)
Score 4/5 (formula FAIL, substitution PASS, final_velocity PASS, distance_25 PASS, graph_area PASS). Lesson 15.22 s, 5 steps, model gpt-5.5.

**Finding Distance from Acceleration**: We’ll answer the bottom example by using the displacement equation, then check the same distance as the area under the velocity–time graph.

1. **Where the answer lives**: Great question: for this example, distance means displacement s. I’m circling the example numbers and the key equation that calculates s directly.
2. **Plug in the given values**: The example gives u equals zero, a equals 2, and t equals 5. So in this blue equation, the starting-velocity part drops out.
3. **Compute the displacement**: Now we do the arithmetic: s equals 0 times 5 plus one half times 2 times 5 squared. That gives 25 metres travelled.
   - board: `s=0+25` · `distance = 25 m`
4. **Check with the v–t graph**: Now check it visually: displacement is the area under the v–t graph. Here velocity rises from 0 to 10 over 5 seconds, so the area is a triangle.
   - board: `½×5×10=25`
5. **Final answer**: Both methods agree: the object travels 25 metres in 5 seconds. Formula and graph are telling the same story—displacement is accumulated velocity over time.
   - board: `same s` · `Answer: 25 m`
   - sketch: `flowchart LR ; A[Given u,a,t] --> B[Use s equation] ; B --> C[Get 25 m] ; A --> D[Find graph area] ; D --> C`

Missing: formula: MISSING any: 0 of 3 matched, need 1

## math_ohm_internal_resistance, run 1

Question: "How do we get the 1.5 A current and the 7.5 V across R in this circuit?" (math_ohm_internal_resistance.jpg)
Score 5/5 (total_resistance PASS, current PASS, internal_drop PASS, terminal_voltage PASS, kirchhoff PASS). Lesson 19.306 s, 6 steps, model gpt-5.5.

**Finding Current and Voltage Across R**: We use the total series resistance, including the battery’s internal resistance, to get the 1.5 A current. Then we multiply that current by the external resistor R to get the 7.5 V drop shown on the graph.

1. **What the circuit is asking**: We’re answering how this circuit gets the 1.5 A current and the 7.5 V across R. The key is that both resistors are in series with the 12 V source.
2. **Add the series resistances**: In one loop, the same current must pass through internal resistance r and the external resistor R. So we add them: 3 ohms plus 5 ohms gives 8 ohms total.
   - board: `Rtotal = 8 Ω`
3. **Use Ohm’s law for the whole loop**: Now apply Ohm’s law to the whole circuit: current equals emf divided by total resistance. Twelve volts divided by 8 ohms is 1.5 amps, matching the arrow on top.
   - board: `12 ÷ 8 = 1.5 A` · `Ohm’s law`
4. **Voltage across the external resistor**: For the question’s second part, use the same current through R. The drop across R is I times R: 1.5 amps times 5 ohms equals 7.5 volts.
   - board: `1.5×5 = 7.5 V`
5. **Why the graph drops twice**: The graph shows the 12 V emf split into two voltage drops: 4.5 V inside the battery and 7.5 V across R. Together, 4.5 plus 7.5 gives the original 12 V.
   - board: `4.5 + 7.5 = 12`
6. **Final answer**: So the current is 1.5 A because the 12 V source pushes through 8 ohms total. The voltage across R is 7.5 V because that same 1.5 A flows through the 5 ohm resistor.
   - board: `same current`
   - sketch: `flowchart LR ; A[12 V source] --> B[3Ω + 5Ω] ; B --> C[8Ω total] ; C --> D[I = 1.5 A] ; D --> E[VR = 7.5 V]`

## math_ohm_internal_resistance, run 2

Question: "How do we get the 1.5 A current and the 7.5 V across R in this circuit?" (math_ohm_internal_resistance.jpg)
Score 4/5 (total_resistance PASS, current PASS, internal_drop FAIL, terminal_voltage PASS, kirchhoff PASS). Lesson 18.649 s, 6 steps, model gpt-5.5.

**Finding the Current and Voltage Across R**: The circuit has a 12 V battery with internal resistance 3 Ω in series with an external 5 Ω resistor. The current is found from total series resistance, then the voltage across R is found using Ohm’s law.

1. **Orient to the series circuit**: We’re answering how the page gets this 1.5 A and the 7.5 V across R. The key is that the battery’s internal resistance r and the outside resistor R are in one series loop.
2. **Add the series resistances**: Because r and R are in series, the same current goes through both, so their resistances add. I’ll write the total resistance beside the two resistor values.
   - board: `Rtotal = 8 Ω`
3. **Use Ohm’s law for the current**: Now the battery supplies 12 V across the total 8 Ω. Using I equals voltage divided by resistance gives 12 divided by 8, which is 1.5 A.
   - board: `I = V/R` · `12÷8 = 1.5 A`
4. **Find voltage across the 5 Ω resistor**: For just R, use that same series current: V_R equals I times R. So 1.5 A times 5 Ω gives 7.5 V, matching the drop labeled IR.
   - board: `same I` · `1.5×5 = 7.5 V`
5. **Check the voltage-step graph**: The graph is a voltage walk around the loop: up 12 V at the battery, then down 4.5 V across r and down 7.5 V across R. The drops add back to the battery rise.
   - sketch: `flowchart LR ; A[12 V source] --> B[Add resistors] ; B --> C[8 ohms total] ; C --> D[I = 1.5 A] ; D --> E[VR = 7.5 V]`
6. **Final answer**: So the current is 1.5 A because the 12 V source drives the total 8 Ω. The voltage across R is 7.5 V because that same 1.5 A flows through the 5 Ω resistor.

Missing: internal_drop: MISSING any: 0 of 4 matched, need 1

## math_parallel_meters, run 1

Question: "Suppose the battery gives 12 V, R1 = 4 Ω, R2 = 2 Ω and R3 = 4 Ω. What do the ammeters A1, A2, A3 and the voltmeters V3 and V4 read?" (math_parallel_meters.png)
Score 5/5 (topology PASS, a2_r1_branch PASS, a3_r2r3_branch PASS, a1_total PASS, v3_v4_split PASS). Lesson 16.605 s, 6 steps, model gpt-5.5.

**Circuit Meter Readings**: We treat the voltmeters as ideal open circuits and ammeters as ideal wires. The battery puts 12 V across two parallel branches: R1 alone, and R2–R3 in series, so the meters follow from Ohm’s law.

1. **Find the two branches**: This circuit asks for meter readings from a 12 V battery. I’ll circle the source, then box the two actual current paths: R1 alone, and R2 plus R3 in series.
2. **R1 branch current gives A2**: Because R1 is directly across the battery, it gets the full 12 V. Ohm’s law gives I equals 12 divided by 4, so A2 reads 3 A.
   - board: `same 12 V` · `I=12/4=3 A`
3. **Bottom branch current gives A3**: Now follow the lower branch: R2 and R3 are in series, so their resistances add. That makes 2 plus 4 equals 6 ohms, and the branch current is 12 over 6, or 2 A through A3.
   - board: `R=2+4=6Ω` · `I=12/6=2 A`
4. **Total current gives A1**: A1 sits before the split, so it measures the total current supplied by the battery. Add the two branch currents: 3 A plus 2 A equals 5 A.
   - board: `3 A` · `2 A` · `3+2=5 A`
5. **Voltmeters across R2 and R3**: V3 and V4 measure voltage drops across the two series resistors. Use the same 2 A branch current: V3 is 2 times 2 equals 4 V, and V4 is 2 times 4 equals 8 V.
   - board: `V=2×2=4 V` · `V=2×4=8 V`
6. **Final readings**: So the answer is: A1 reads 5 A, A2 reads 3 A, A3 reads 2 A, V3 reads 4 V, and V4 reads 8 V. Nice check: 4 V plus 8 V makes the 12 V battery.
   - board: `V4=8 V`
   - sketch: `flowchart TD ; A[12 V source] --> B[Parallel split] ; B --> C[R1: 4 ohm] ; B --> D[R2+R3: 6 ohm] ; C --> E[A2 = 3 A] ; D --> F[A3 = 2 A] ; E --> G[A1 = 5 A] ; F --> G`

## math_parallel_meters, run 2

Question: "Suppose the battery gives 12 V, R1 = 4 Ω, R2 = 2 Ω and R3 = 4 Ω. What do the ammeters A1, A2, A3 and the voltmeters V3 and V4 read?" (math_parallel_meters.png)
Score 5/5 (topology PASS, a2_r1_branch PASS, a3_r2r3_branch PASS, a1_total PASS, v3_v4_split PASS). Lesson 19.261 s, 6 steps, model gpt-5.5.

**Parallel Branch Readings**: The circuit has a 12 V supply feeding two parallel branches: one branch with R1, and one branch with R2 and R3 in series. We compute branch currents and voltage drops to get A1, A2, A3, V3, and V4.

1. **Find the two branches**: We’ll answer the readings by treating this as a 12 V supply across two parallel paths. I’m circling the battery, then the R1 path and the bottom R2–R3 path.
2. **Parallel means each branch gets 12 V**: Because these two branches connect between the same left and right rails, each whole branch has the full 12 V across it. So R1 gets 12 V, and the series pair R2 plus R3 also gets 12 V.
   - board: `12 V branch` · `12 V branch` · `same two nodes`
3. **A2 reads the R1 branch current**: Now use Ohm’s law on the middle branch: I equals V over R, so 12 divided by 4 is 3 A. That is the current through R1, so A2 reads 3 A.
   - board: `12/4 = 3 A` · `A2 = 3 A`
4. **A3 reads the bottom branch current**: For the bottom branch, R2 and R3 are in series, so add them: 2 plus 4 equals 6 ohms. The branch current is 12 divided by 6, so A3 reads 2 A.
   - board: `series: add` · `2+4=6 Ω` · `A3 = 2 A`
5. **Split the voltage across R2 and R3**: The same 2 A flows through both bottom resistors. So V3 across R2 is 2 times 2, giving 4 V; V4 across R3 is 2 times 4, giving 8 V.
   - board: `I = 2 A` · `V3 = 4 V` · `V4 = 8 V`
6. **A1 reads the total current**: A1 is before the split, so it reads the total current from the battery: add the two branch currents, 3 A plus 2 A. Final readings: A1 is 5 A, A2 is 3 A, A3 is 2 A, V3 is 4 V, and V4 is 8 V.
   - board: `3+2=5 A`
   - sketch: `flowchart TD ; A[12 V supply] --> B[Parallel branches] ; B --> C[R1: 4 ohm] ; B --> D[R2+R3: 6 ohm] ; C --> E[A2 = 3 A] ; D --> F[A3 = 2 A] ; E --> G[A1 = 5 A] ; F --> G`

