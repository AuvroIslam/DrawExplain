# Lesson transcripts: L2

Backend 6dbe976 (Simulate procedures faithfully, deepen board colours). + general simulate-don't-shortcut rule.
Every lesson of the benchmark, as the student hears it (narration) and sees it (board text, sketch), with the automatic checks. Board texts attached to a lettered node show the letter first. Made by backend/scripts/eval_lessons.py.

## dijkstra_AtoE, run 1

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 5/5 (init PASS, relax_A PASS, relax_I_all PASS, order PASS, answer PASS). Lesson 20.032 s, 5 steps, model gpt-5.5.

**Shortest Path from A to E**: We’ll answer the question by tracing Dijkstra’s Algorithm on this graph, starting at A and stopping when E becomes the next settled vertex. The shortest path will come from repeatedly choosing the cheapest unfinished vertex and relaxing its edges.

1. **Orient: start at A, goal E**: This page is asking us to trace Dijkstra; for your question, we start at A and want the cheapest route to E. I’ll circle A in blue and E in green so we keep source and goal straight.
   - board: `a: dist 0 ✓`
2. **Iteration 1: relax A’s neighbors**: Dijkstra settles A first because its distance is 0. From A, we write tentative costs to every neighbor: B gets 5, I gets 1, G gets 9, and H gets 18.
   - board: `a -> ?: +1` · `∞→1` · `b: ∞→5`
3. **Iteration 2: settle I, improve toward E**: Next we choose I, the smallest unfinished distance, 1. From I, E becomes 1 plus 2 equals 3, and G improves from 9 to 4; C would be 7, not our best route to E yet.
   - board: `1 ✓` · `? -> e: +2` · `e: ∞→3`
4. **Iteration 3: E is now settled**: Now the smallest unfinished distance is E with 3, so Dijkstra locks it in. That means no later path can beat cost 3, because all edge weights are non-negative.
   - board: `e: 3 ✓ done`
5. **Answer: path A → I → E**: So the shortest path from A to E is A to I to E. Add the edge weights: 1 plus 2 gives total cost 3.
   - board: `a -> ?: +1` · `? -> e: +2` · `a+e: total = 3`
   - sketch: `flowchart LR ; A[Start A] --> N[Pick min] ; N --> R[Relax edges] ; R --> E{E picked?} ; E -->\|no\| N ; E -->\|yes\| P[A-I-E cost 3]`

## dijkstra_AtoE, run 2

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 4/5 (init PASS, relax_A PASS, relax_I_all FAIL, order PASS, answer PASS). Lesson 16.628 s, 5 steps, model gpt-5.5.

**Shortest Path from A to E**: We’ll run Dijkstra’s algorithm on this graph starting at A, stopping when E becomes the next settled vertex. The shortest A-to-E cost is 3, through A → I → E.

1. **Orient: start and goal**: You asked for the shortest path from A to E, so this graph is our playground. I’ll circle A as the source and E as the destination, then we’ll trace Dijkstra’s cheapest-first choices.
   - board: `a: dist=0`
2. **Initialize A’s neighbors**: Dijkstra starts with A at distance 0, then relaxes every edge leaving A. So B gets 5, H gets 18, G gets 9, and I gets 1 as tentative best costs.
   - board: `a -> b: +5` · `b: ∞→5` · `a -> ?: +1` · `∞→1`
3. **Pick I, then relax from I**: Now pick the unsettled vertex with the smallest tentative distance: I, with 1. From I, the edge to E costs 2, so A to I to E gives 1 + 2 = 3.
   - board: `1 ✓ done` · `? -> e: +2` · `e: ∞→3`
4. **Check the stopping condition**: After I is settled, E has tentative distance 3. Every other visible tentative option is at least 4 or 5, so Dijkstra would choose E next, which locks in the answer.
   - board: `e: 3 ✓ shortest`
5. **Final path**: So the shortest path from A to E is A → I → E, with total cost 3. Dijkstra works because it always settles the cheapest unfinished vertex next.
   - board: `a -> ?: +1` · `? -> e: +2` · `a+e: total = 3`
   - sketch: `flowchart LR ; A[Start A] --> N[Relax neighbors] ; N --> I[Pick I] ; I --> E[Update E=3] ; E --> S[Settle E] ; S --> R[Path A-I-E]`

Missing: relax_I_all: MISSING \| MISSING \| e gives 1 + 2 = 3

## dijkstra_AtoE, run 3

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 5/5 (init PASS, relax_A PASS, relax_I_all PASS, order PASS, answer PASS). Lesson 21.247 s, 6 steps, model gpt-5.5.

**Shortest Path from A to E**: We’ll run Dijkstra’s algorithm on this graph, starting at A, until E’s shortest distance is settled. The shortest route is found by repeatedly choosing the unsettled vertex with the smallest known cost and relaxing its edges.

1. **Start at A**: You asked for the shortest path from A to E, so this graph is where the answer lives. I’ll circle A as the source and E as our destination.
   - board: `a: dist 0 ✓`
2. **Relax A’s neighbors**: From A, Dijkstra records the first tentative costs to every neighbor. Follow my blue arrows: B gets 5, I gets 1, G gets 9, and H gets 18.
   - board: `a -> b: +5` · `b: ∞→5 via A` · `a -> ?: +1` · `∞→1 via A`
3. **Pick I next**: Now Dijkstra chooses the smallest unsettled distance: I has 1, so I becomes done. Relaxing from I improves G to 4, E to 3, and C to 7.
   - board: `1 ✓ done` · `? -> g: 1+3` · `g: 9→4 via I`
4. **E is settled**: The smallest unsettled distance is now E with cost 3, so Dijkstra locks it in. Because E is the destination you asked about, we can stop here: no later path can beat 3.
   - board: `e: 3 ✓ shortest`
5. **Read the route backward**: To recover the actual path, follow the remembered predecessors backward: E came from I, and I came from A. So the forward path is A to I to E.
   - board: `e -> ?: prev` · `? -> a: prev` · `a -> ?: +1` · `? -> e: +2`
6. **Answer**: Final answer: the shortest path from A to E is A → I → E, with total cost 1 + 2 = 3. That is exactly what Dijkstra proves when E is locked.
   - board: `a+e: A→I→E cost 3`
   - sketch: `flowchart LR ; A[Start A] --> B[Set neighbors] ; B --> C[Pick smallest] ; C --> D[Relax edges] ; D --> E{Is E done?} ; E -->\|no\| C ; E -->\|yes\| F[Return path]`

## tcp_cwnd, run 1

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 4/5 (starts_at_1 PASS, doubling PASS, concrete_threshold FAIL, additive PASS, timeout PASS). Lesson 15.703 s, 6 steps, model gpt-5.5.

**CongWin: Start to Timeout**: This page lays out TCP’s congestion-window story: grow fast in Slow Start, grow gently in Additive Increase, then cut back when a timeout signals congestion.

1. **Orient: the path we’ll follow**: Your question lives in these three rules: start small, grow, then timeout cuts back. I’m circling the roadmap so we can track CongWin from birth to loss.
2. **begin at 1 MSS**: At the start, TCP is deliberately cautious: CongWin equals 1 MSS. That means only one segment’s worth is allowed in flight before ACKs prove the path can handle more.
   - board: `start: cwnd=1`
3. **Slow Start grows fast**: Now every successful ACK adds 1 to cwnd, so within a round trip the window roughly doubles. This is the exponential part: 1 becomes 2, then 4, then 8, until the threshold.
   - board: `until threshold` · `1→2→4→8`
4. **after threshold, growth slows**: After Slow Start reaches the threshold, TCP switches to Additive Increase. Each ACK adds only 1/n, so over one RTT the total gain is about one MSS, not doubling anymore.
   - board: `+1 per RTT`
5. **timeout triggers the cut**: When a timeout occurs, TCP treats that as strong congestion evidence. The threshold becomes half of the old CongWin, and CongWin itself is reset all the way to 1 MSS.
6. **Answer: the full change**: So the answer is: CongWin starts at 1 MSS, rises exponentially until the threshold, then rises additively, and on timeout drops back to 1 MSS while the threshold is set to half the previous CongWin.
   - board: `grow then reset`
   - sketch: `flowchart LR ; A[Start 1 MSS] --> B[Slow Start] ; B --> C[Reach threshold] ; C --> D[Additive Increase] ; D --> E[Timeout] ; E --> F[Back to 1 MSS]`

Missing: concrete_threshold: MISSING

## tcp_cwnd, run 2

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 4/5 (starts_at_1 PASS, doubling PASS, concrete_threshold FAIL, additive PASS, timeout PASS). Lesson 17.136 s, 6 steps, model gpt-5.5.

**CongWin Growth Until Timeout**: This page summarizes TCP congestion control: CongWin starts at 1 MSS, grows quickly in Slow Start, then grows gently in Additive Increase, and drops sharply when a timeout happens.

1. **Find the path**: Great question: we follow CongWin from the start down to the timeout rule. I’ll circle the three stages that form the story: fast growth, gentle growth, then a timeout drop.
2. **Start at 1 MSS**: The initial state is explicit: CongWin begins at 1 MSS. So before any ACKs arrive, the sender is allowed just one maximum-sized segment in flight.
   - board: `start value`
3. **Slow Start doubles per RTT**: During Slow Start, every successful ACK increases cwnd by 1. Because one window of packets produces one window of ACKs, the window roughly doubles each RTT: 1, 2, 4, 8, until the threshold.
   - board: `1→2→4→8`
4. **Switch at threshold**: Slow Start does not continue forever; it stops when CongWin reaches the threshold value. My arrow shows that crossing point sends us into Additive Increase, the congestion-avoidance mode.
   - board: `then AI` · `after threshold`
5. **Additive Increase grows slowly**: After that, each ACK adds only 1/n, where n is the current CongWin. That means the total growth is about 1 MSS per RTT, much calmer than Slow Start.
   - board: `+1 MSS/RTT`
6. **Timeout cuts it down**: Now the timeout: TCP sets Threshold to half of the current CongWin, then resets CongWin to 1 MSS. So the answer is: grow 1→2→4… to threshold, then linear +1 per RTT, then timeout drops back to 1 MSS.
   - sketch: `flowchart LR ; A[Start 1 MSS] --> B[Slow Start] ; B --> C[Reach threshold] ; C --> D[Additive Increase] ; D --> E[Timeout] ; E --> F[CongWin 1 MSS]`

Missing: concrete_threshold: MISSING

## tcp_cwnd, run 3

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 3/5 (starts_at_1 PASS, doubling FAIL, concrete_threshold FAIL, additive PASS, timeout PASS). Lesson 18.256 s, 6 steps, model gpt-5.5.

**CongWin from Start to Timeout**: This page describes the TCP congestion window path: start at 1 MSS, grow fast in Slow Start, then grow gently in Additive Increase, and finally drop on a timeout. The key timeout answer is: threshold becomes half of the current CongWin, and CongWin resets to 1 MSS.

1. **Find the whole path**: Great question—this slide is the CongWin story from the very beginning to a timeout. I’ll circle the three phases: grow fast, grow slowly, then cut down when loss appears.
2. **Start: CongWin is tiny**: At the start, TCP deliberately begins cautious: CongWin equals 1 MSS. Think of this as sending one segment first, just to test the network.
   - board: `initial cwnd`
3. **Slow Start: each ACK adds 1**: Now each successful ACK increases cwnd by 1. Because a larger window creates more ACKs per round, the total window growth becomes exponential until the threshold is reached.
   - board: `double per RTT`
4. **After threshold: additive increase**: Once Slow Start hits the threshold, TCP switches to Additive Increase. Here each ACK adds only 1/n, so across about one RTT the window grows by just 1 MSS total.
   - board: `switch mode` · `+1 per RTT`
5. **Timeout: multiplicative decrease**: Now answer the timeout part: if a time-out occurs, TCP sets the threshold to half of the current CongWin, then resets CongWin all the way back to 1 MSS.
   - board: `restart cautious`
6. **Big picture answer**: So from start to timeout: CongWin goes 1 MSS, rises exponentially to the threshold, rises linearly after that, then timeout cuts the threshold in half and sends CongWin back to 1 MSS.
   - board: `grow then drop`
   - sketch: `flowchart LR ; A[Start 1 MSS] --> B[Slow Start] ; B --> C[Hit threshold] ; C --> D[Additive Increase] ; D --> E[Timeout] ; E --> F[cwnd 1 MSS]`

Missing: doubling: MISSING; concrete_threshold: MISSING

## flowchart_invalid_twice, run 1

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 23.269 s, 6 steps, model gpt-5.5.

**Invalid Twice in the Validation Loop**: This flowchart keeps sending invalid input through the error path and back to “Read input.” If the input is invalid twice, the loop repeats twice before it can move on.

1. **Find the loop that answers it**: Great question—invalid twice means we follow the No path twice. I’m circling the decision where the flowchart checks each input.
2. **First input is read and checked**: We start by reading the first input, then the arrow carries it into the validity check. Think of this as attempt number one.
   - board: `attempt 1`
3. **First invalid answer loops back**: If that first input is invalid, we take the red No branch, show an error, and jump back to read input again. I’ll mark that as one failed try.
   - board: `invalid` · `fail #1`
4. **Second invalid answer repeats the same loop**: Now the back arrow returns us to read another input. If the second input is invalid too, the exact same No branch happens again: error, then back to read input.
   - board: `retry` · `attempt 2` · `fail #2`
5. **Only valid input exits the loop**: After two invalid inputs, the program is still not at End—it asks again. Only when Valid? is Yes does it process the data and finish.
   - board: `valid exits` · `finish`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`
6. **Answer: invalid twice means two retries**: So the answer is: invalid twice causes two trips through Show error, and then the flowchart asks for input a third time. It stops looping only after a valid input passes the check.

## flowchart_invalid_twice, run 2

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 17.173 s, 5 steps, model gpt-5.5.

**Invalid Input Twice in the Loop**: This flowchart keeps asking for input until the decision says it is valid. If the input is invalid twice, the same error-and-retry path happens two times before any valid input can move on.

1. **Find the loop that answers it**: Great question: invalid twice means we follow the ‘No’ branch twice. I’m circling the decision because every repeat is controlled right here.
2. **First invalid input**: On the first try, we read input, test it, and the answer is No. Follow my red arrow down to Show error: that is the first rejection.
   - board: `check it` · `invalid #1` · `1st error`
3. **Loop back for try two**: After showing the error, the flow loops back into Read input. That means the program does not end; it asks again for a new attempt.
   - board: `ask again` · `try #2`
4. **Second invalid input**: Now the second input is checked the same way. If it is invalid again, we take No again and show the error a second time.
   - board: `check again` · `invalid #2` · `2nd error`
5. **Answer: still not finished**: So after two invalid inputs, the program has shown two errors and is back at Read input for a third try. It only reaches Process data when Valid? finally says Yes.
   - board: `try #3 next` · `only if valid` · `valid stops loop`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`

## flowchart_invalid_twice, run 3

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 16.284 s, 6 steps, model gpt-5.5.

**Invalid Twice in the Validation Loop**: If the input is invalid twice, the flowchart takes the “No” branch twice, shows the error twice, and returns to “Read input” each time. It only moves to “Process data” after a valid input is entered.

1. **Find the loop that answers it**: Great question: invalid twice means we follow the repeat path twice. I’ll circle the decision point, because that diamond controls whether we continue or loop back.
   - board: `test each time`
2. **First invalid input**: Start by reading the first input, then check Valid?. Since it is invalid, we take the No arrow down to Show error.
   - board: `check it` · `No` · `error #1`
3. **Loop back and try again**: After showing the error, the flowline loops back up to Read input. That means the program asks again instead of ending or processing bad data.
   - board: `ask again` · `attempt #2`
4. **Second invalid input**: Now the second input is also invalid, so the exact same rule fires again. We go from Valid? down to Show error a second time, then loop back again.
   - board: `check #2` · `No again` · `error #2`
5. **What happens next?**: So after two invalid inputs, the program is back at Read input waiting for attempt three. It has not reached Process data yet, because the Yes branch only happens after Valid? passes.
   - board: `attempt #3 next`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`
6. **Plain answer**: Final answer: invalid twice means two error messages and two trips around the loop. The program keeps asking until one input is valid.

## math_calvin_cycle, run 1

Question: "How many ATP and NADPH does this cycle use to fix 3 CO₂, and what happens to the 6 GAP?" (math_calvin_cycle.png)
Score 5/5 (fixation PASS, reduction_cost PASS, regeneration_cost PASS, totals PASS, gap_split PASS). Lesson 18.32 s, 6 steps, model gpt-5.5.

**Calvin Cycle: Energy Cost and GAP Fate**: This diagram shows the Calvin cycle fixing 3 CO₂. For 3 CO₂, it uses 9 ATP and 6 NADPH total, while 1 GAP exits and 5 GAP are recycled to rebuild RuBP.

1. **Find the bookkeeping target**: We’re answering the energy bill for fixing 3 CO₂, so I’ll circle the entry point and the GAP output area. The whole page is tracking carbon plus ATP and NADPH through the Calvin cycle.
2. **First ATP spend: reduction setup**: First, 3 CO₂ become six 3-P-glycerate molecules, then this red ATP arrow upgrades them. Count it right here: 6 ATP become 6 ADP, so that is the first six ATP used.
   - board: `carbon fixed` · `ATP used: 6`
3. **NADPH spend makes GAP**: Next, NADPH supplies the reducing power. Follow my blue arrow: 6 NADPH/H⁺ turn into 6 NADP⁺, producing six GAP molecules and releasing 6 Pi.
   - board: `reduces` · `NADPH used: 6`
4. **Split the six GAP**: Now the important GAP split: one GAP peels off to the right as product. The other five GAP stay in the cycle, and the page labels them as 5x GAP going downward.
   - board: `1 exits` · `5 recycle` · `sugar output`
5. **Extra ATP regenerates RuBP**: Those five recycled GAP are rearranged into three ribulose-5-P, then phosphorylated back to three RuBP. This last red ATP step uses 3 more ATP, so total ATP is 6 plus 3 equals 9.
   - board: `rearrange` · `6+3=9 ATP`
6. **Plain answer**: So for fixing 3 CO₂, the cycle spends 9 ATP and 6 NADPH. Of the 6 GAP made, 1 GAP leaves as carbohydrate product and 5 GAP regenerate the CO₂ acceptor.
   - board: `regenerates RuBP`
   - sketch: `flowchart LR ; A[3 CO2 fixed] --> B[6 3-PGA] ; B --> C[Use 6 ATP] ; C --> D[Use 6 NADPH] ; D --> E[6 GAP] ; E --> F[1 exits] ; E --> G[5 regenerate RuBP]`

## math_calvin_cycle, run 2

Question: "How many ATP and NADPH does this cycle use to fix 3 CO₂, and what happens to the 6 GAP?" (math_calvin_cycle.png)
Score 5/5 (fixation PASS, reduction_cost PASS, regeneration_cost PASS, totals PASS, gap_split PASS). Lesson 18.842 s, 6 steps, model gpt-5.5.

**Calvin Cycle Inputs and GAP Fate**: This page tracks the Calvin cycle for fixing 3 CO₂: ATP and NADPH are spent in two energy-using phases, and the 6 GAP split into one product GAP plus five recycled GAP.

1. **Find the accounting frame**: Great question—this whole diagram is the bookkeeping for fixing 3 CO₂. I’m circling the starting CO₂ and the cycle product area so we can count only what this turn uses and makes.
2. **First ATP investment: phosphorylation**: First, ATP pushes 3-P-glycerate up to 1,3-bP-glycerate. Follow my arrow: the red labels show 6 ATP spent and 6 ADP coming out.
   - board: `adds phosphate`
3. **NADPH reduction makes 6 GAP**: Next, NADPH supplies high-energy electrons to reduce 1,3-bP-glycerate into GAP. The blue NADPH becomes NADP+, and phosphate is released as Pi.
   - board: `reduction`
4. **Split the 6 GAP**: Now the key answer about GAP: one GAP exits as sugar-building material, while five GAP stay in the cycle. I’m boxing the split so the 6 becomes 1 out plus 5 recycled.
   - board: `6 = 1 + 5`
5. **Second ATP investment regenerates RuBP**: Those five recycled GAP are rearranged into ribulose-5-P, then 3 ATP regenerate ribulose-1,5-bP. So the cycle spends another 3 ATP here to reset the CO₂ acceptor.
   - board: `rearrange` · `reset acceptor`
6. **Final count**: So for 3 CO₂, the cycle uses 9 ATP total and 6 NADPH. The 6 GAP become one net GAP product plus five GAP recycled to rebuild RuBP.
   - board: `6 + 3 = 9 ATP` · `6 NADPH used` · `5 recycle`
   - sketch: `flowchart LR ; A[3 CO2 fixed] --> B[6 3-PGA] ; B --> C[Use 6 ATP] ; C --> D[Use 6 NADPH] ; D --> E[6 GAP] ; E --> F[1 GAP exits] ; E --> G[5 regenerate RuBP]`

## cs_bst_insert, run 1

Question: "How would you insert 5 into this binary search tree? Show the comparisons, where 5 ends up, and the in-order traversal afterwards." (cs_bst_insert.png)
Score 5/5 (left_at_8 PASS, right_at_3_left_at_6 PASS, right_child_of_4 PASS, search_path PASS, inorder_after PASS). Lesson 17.627 s, 6 steps, model gpt-5.5.

**Inserting 5 in the BST**: We insert 5 by comparing it with each node on the search path: smaller goes left, larger goes right. After placing 5, an in-order traversal lists the tree in sorted order.

1. **Start at the root**: We’re inserting 5 into this binary search tree, so we start at the root I just circled. Rule: compare, then go left if smaller or right if bigger.
   - board: `start here`
2. **Compare 5 with 8**: First comparison: 5 is less than 8, so follow my blue arrow to the left child. That lands us at 3.
   - board: `5 < 8` · `go left`
3. **Compare 5 with 3**: Now compare at 3: 5 is greater than 3, so we turn right. Follow the arrow to node 6.
   - board: `5 > 3` · `go right`
4. **Compare 5 with 6 and insert**: At 6, 5 is less than 6, so it belongs on the left side. The left child is 4, so compare once more: 5 is greater than 4, and 4 has no right child, so 5 goes there.
   - board: `5 < 6` · `go left` · `5 > 4`
5. **In-order traversal after insertion**: For in-order traversal, read left subtree, then node, then right subtree. After adding 5 as 4’s right child, the sorted order is 1, 3, 4, 5, 6, 7, 8, 10, 13, 14.
   - board: `1,3,4,5,6,7,8,10,13,14` · `visit after 4`
   - sketch: `flowchart TD ; A[Compare node] ; B{5 smaller?} ; C[Go left] ; D[Go right] ; E[Empty spot] ; F[Insert 5] ; A --> B ; B -->\|yes\| C ; B -->\|no\| D ; C --> A ; D --> A ; A --> E ; E --> F`
6. **Final answer**: So the full comparison path is 8 to 3 to 6 to 4, then insert 5 as the right child of 4. That keeps the BST rule true everywhere.
   - board: `8→3→6→4`

## cs_bst_insert, run 2

Question: "How would you insert 5 into this binary search tree? Show the comparisons, where 5 ends up, and the in-order traversal afterwards." (cs_bst_insert.png)
Score 5/5 (left_at_8 PASS, right_at_3_left_at_6 PASS, right_child_of_4 PASS, search_path PASS, inorder_after PASS). Lesson 17.658 s, 6 steps, model gpt-5.5.

**Inserting 5 into the BST**: We’ll insert 5 by following the binary-search-tree rule: smaller values go left, larger values go right. The new 5 becomes a leaf under 4, and the in-order traversal becomes sorted: 1, 3, 4, 5, 6, 7, 8, 10, 13, 14.

1. **Start at the root**: We’re inserting 5 into this binary search tree, so we begin at the root I’m circling. At each node, compare 5 with the node value, then go left if smaller or right if larger.
   - board: `start here`
2. **Compare 5 with 8**: First comparison: 5 is less than 8, so follow my arrow to the left child. That lands us on 3, because BST left branches hold smaller values.
   - board: `5 < 8` · `go left`
3. **Compare 5 with 3**: Now compare 5 with 3: 5 is bigger, so we move right from 3. The right child is 6, so 5 must be somewhere in 6’s left side if it fits.
   - board: `5 > 3` · `go right`
4. **Compare 5 with 6**: At 6, 5 is smaller, so follow the left branch. We arrive at 4, and now the search is narrowing between 4 and 6.
   - board: `5 < 6` · `go left`
5. **Insert as 4’s right child**: At 4, 5 is bigger, so it would go to 4’s right. That spot is empty, so we draw the new node 5 there as a leaf.
   - board: `5 > 4` · `insert`
6. **In-order traversal after insertion**: For in-order traversal, read left subtree, then node, then right subtree. After inserting 5, the sorted order is 1, 3, 4, 5, 6, 7, 8, 10, 13, 14.
   - board: `between 4 and 6` · `1,3,4,5,6,7,8,10,13,14`
   - sketch: `flowchart TD ; A[Compare at node] ; B{5 smaller?} ; C[Go left] ; D[Go right] ; E[Empty spot] ; F[Insert 5] ; A --> B ; B -->\|yes\| C ; B -->\|no\| D ; C --> A ; D --> A ; A --> E ; E --> F`

## cs_bfs_dfs, run 1

Question: "In which order does breadth-first search visit the nodes if it starts at A and takes neighbours in alphabetical order? How would depth-first search from A differ?" (cs_bfs_dfs.png)
Score 5/5 (bfs_order PASS, bfs_queue PASS, bfs_levels PASS, dfs_order PASS, dfs_mechanism PASS). Lesson 21.991 s, 6 steps, model gpt-5.5.

**BFS vs DFS from A**: We’ll run breadth-first search on the graph starting at A, using alphabetical neighbor order, then compare it with depth-first search on the same graph. The key difference is that BFS finishes one layer at a time, while DFS follows one branch as far as it can before backtracking.

1. **Start at A**: This graph question lives at A: both searches start there, and alphabetical order decides ties. I’ll mark A as visited first.
   - board: `a: visit 1`
2. **BFS layer 1: A’s neighbors**: For BFS, we visit A’s direct neighbors next: B, C, then E in alphabetical order. These are the whole first layer around A.
   - board: `a -> b: next` · `a -> c: next` · `a -> e: next` · `b: visit 2`
3. **BFS layer 2: expand in queue order**: Now BFS expands the queue in order: from B we add D and F, from C we add G, and E only points to F which is already discovered. So BFS order is A, B, C, E, D, F, G.
   - board: `b -> d: add` · `b -> f: add` · `c -> g: add` · `d: visit 5`
4. **DFS: go deep before wide**: Depth-first search differs right away: from A it chooses B first, then keeps going to B’s alphabetically earliest unvisited neighbor, D. After D ends, it backtracks to B and visits F.
   - board: `a -> b: DFS 2` · `b -> d: DFS 3` · `b -> f: DFS 4` · `d: dead end`
5. **DFS continues through F to E**: At F, the unvisited neighbor is E, so DFS follows the bottom connection across to E. Notice how DFS reaches E before C, unlike BFS.
   - board: `f -> e: DFS 5` · `e: before C`
6. **Final orders**: After E, DFS backtracks to A, then visits C and finally G. Final answer: BFS is A, B, C, E, D, F, G; DFS is A, B, D, F, E, C, G.
   - board: `a+b+c+e+d+f+g: BFS: layers` · `a+b+c+e+d+f+g: DFS: branches`
   - sketch: `flowchart LR ; A[Start A] --> B[Choose alphabetically] ; B --> C{BFS?} ; C -->\|yes\| D[Visit by layers] ; C -->\|no\| E[Go deep] ; D --> F[BFS order] ; E --> G[DFS order]`

## cs_bfs_dfs, run 2

Question: "In which order does breadth-first search visit the nodes if it starts at A and takes neighbours in alphabetical order? How would depth-first search from A differ?" (cs_bfs_dfs.png)
Score 5/5 (bfs_order PASS, bfs_queue PASS, bfs_levels PASS, dfs_order PASS, dfs_mechanism PASS). Lesson 20.381 s, 6 steps, model gpt-5.5.

**BFS vs DFS from A**: We’ll run breadth-first search and depth-first search on the pictured graph, starting at A and using alphabetical neighbour order. BFS visits by layers; DFS dives down one branch before backing up.

1. **Start at A and list neighbours**: We start at the A I just circled. Alphabetical neighbours of A are B, C, then E, so that order controls both searches.
   - board: `a: start` · `a -> b: 1st neighbour`
2. **BFS visits level 0 then level 1**: For BFS, think queue: visit A first, then enqueue its neighbours B, C, E. Those three are the whole first layer around A.
   - board: `a: BFS 1`
3. **BFS queue expands B then C then E**: Now BFS removes B next, so it discovers D and F in alphabetical order. Then C discovers G, and E adds nothing new because F is already discovered through that bottom edge.
   - board: `b: BFS 2` · `b -> d: discover` · `b -> f: discover` · `c: BFS 3`
4. **Finish the BFS order**: So the BFS visit order is A, B, C, E, D, F, G. The key is layer-by-layer: distance 0, then distance 1, then distance 2.
   - board: `e: BFS 4` · `d: BFS 5` · `f: BFS 6` · `g: BFS 7`
5. **DFS dives before it sweeps**: DFS also starts at A and chooses B first, but now it dives. From B it takes D, backs up, then takes F, and from F reaches E before returning to C and G.
   - board: `a -> b: DFS` · `b -> d: dive` · `b -> f: next` · `f -> e: via edge`
6. **Final answer: two different orders**: Final answer: BFS is A, B, C, E, D, F, G; DFS is A, B, D, F, E, C, G. Same alphabetical rule, different strategy: queue spreads out, recursion dives in.
   - board: `a+b+c+e+d+f+g: BFS: layers` · `a+b+c+e+d+f+g: DFS: dive`
   - sketch: `flowchart LR ; A[Start A] --> B[Alphabetical neighbours] ; B --> C{Strategy?} ; C --> D[BFS queue] ; C --> E[DFS recursion] ; D --> F[Layer order] ; E --> G[Deep order]`

## cs_dijkstra_a_to_e, run 1

Question: "Use Dijkstra's algorithm starting at A: what are the shortest distances to the other nodes, and what is the shortest path from A to E?" (cs_dijkstra_a_to_e.png)
Score 5/5 (b_stays_4 PASS, d_is_5 PASS, e_is_10 PASS, path_a_c_e PASS, via_d_is_12 PASS). Lesson 18.284 s, 6 steps, model gpt-5.5.

**Dijkstra from A to E**: We’ll run Dijkstra’s algorithm on the weighted graph, starting at A. The final shortest distances are A=0, C=2, B=4, D=5, E=10, and the shortest path to E is A → C → E.

1. **Set up the start**: This graph is a Dijkstra shortest-path problem starting at A. I’ll circle A as distance 0, and every other node starts unknown until an edge improves it.
   - board: `a: dist=0 ✓` · `c+b+d+e: start at ∞`
2. **Relax A’s edges**: From the finished A, follow its two edges. A to C costs 2, so C becomes 2; A to B costs 4, so B becomes 4.
   - board: `a -> c: +2` · `c: ∞→2` · `a -> b: +4`
3. **Choose C, then relax from C**: The smallest unfinished distance is C=2, so C is locked in next. From C, B would be 7, D becomes 5, and E becomes 10.
   - board: `c: 2 ✓ done` · `d: ∞→5` · `e: ∞→10`
4. **Choose B, check its edge**: Now B=4 is the smallest unfinished node, so we lock B. Its edge to D gives 4+10=14, which is worse than D’s 5, so nothing changes.
   - board: `b: 4 ✓ done` · `b -> d: 14 > 5`
5. **Choose D, check E**: Next D=5 is locked. Going from D to E costs 5+7=12, still worse than E’s current 10, so E stays at 10.
   - board: `d: 5 ✓ done` · `d -> e: 12 > 10`
6. **Final answer**: Last, E=10 is locked, so we are done. The shortest path to E follows the predecessor links: A to C to E, with total cost 2+8=10.
   - board: `a -> c: path` · `c -> e: total 10` · `e: E=10 ✓`
   - sketch: `flowchart LR ; A[Start A=0] --> C[Pick smallest] ; C --> R[Relax edges] ; R --> U[Update distances] ; U --> D[Mark done] ; D -->\|repeat\| C ; D --> F[All settled]`

## cs_dijkstra_a_to_e, run 2

Question: "Use Dijkstra's algorithm starting at A: what are the shortest distances to the other nodes, and what is the shortest path from A to E?" (cs_dijkstra_a_to_e.png)
Score 5/5 (b_stays_4 PASS, d_is_5 PASS, e_is_10 PASS, path_a_c_e PASS, via_d_is_12 PASS). Lesson 18.624 s, 5 steps, model gpt-5.5.

**Dijkstra from A to E**: We’ll run Dijkstra’s algorithm on this weighted graph starting at A. The final shortest distances are A=0, C=2, B=4, D=5, E=10, and the shortest path to E is A → C → E.

1. **Start at A**: We’re finding shortest distances from A, so I’ll circle A as the start. Dijkstra begins with A at distance 0 and every other node unknown, or infinity.
   - board: `a: dist=0 ✓` · `c: ∞`
2. **Relax A’s edges**: From A, we update its two neighbors. The edge to C costs 2, and the edge to B costs 4, so those become our first tentative distances.
   - board: `a -> c: +2` · `c: ∞→2` · `a -> b: +4` · `b: ∞→4`
3. **Visit C next**: The smallest unfinished distance is C with 2, so Dijkstra locks it in. From C, we improve D to 5, B would be 7 so it stays 4, and E becomes 10.
   - board: `c: 2 ✓ done` · `c -> d: 2+3` · `d: ∞→5`
4. **Visit B, then D**: Next smallest is B at 4, but its routes do not beat what we already have. Then D at 5 also cannot improve E, because 5 plus 7 is 12, worse than 10.
   - board: `b: 4 ✓ done` · `d -> e: 5+7=12` · `d: 5 ✓ done`
5. **Final answer: path to E**: Now E is the last closest node at distance 10. Tracing predecessors gives A to C to E, so the shortest path is A → C → E with total cost 10.
   - board: `a -> c: path` · `c -> e: +8` · `e: 10 ✓ done`
   - sketch: `flowchart LR ; A[Start A] ; B[Pick smallest] ; C[Relax edges] ; D[Mark done] ; E[All settled] ; A-->B ; B-->C ; C-->D ; D-->B ; D-->E`

## cs_prim_mst, run 1

Question: "Using Prim's algorithm starting from A, which edges are added to the minimum spanning tree, in what order, and what is the total weight?" (cs_prim_mst.png)
Score 4/5 (edges_ad_df_ab PASS, edges_be_ce_eg PASS, prim_order PASS, total_39 PASS, skips_cycle_edges FAIL). Lesson 17.798 s, 6 steps, model gpt-5.5.

**Prim’s Algorithm from A**: We will run Prim’s algorithm on the graph starting at A. At each step, we add the cheapest edge that connects the growing tree to one new vertex, then total the chosen weights.

1. **Start at A**: We’re answering the Prim’s question by growing a tree from A. I’ll circle A as the starting island, and the rule is: always take the cheapest edge leaving our current tree.
   - board: `start`
2. **Pick A–D first**: From A, the available edges are A–D with 5 and A–B with 7. The smaller one is 5, so Prim adds A–D first.
   - board: `add 5`
3. **Pick D–F next**: Now the tree is A and D, so we compare edges leaving either one: A–B 7, D–B 9, D–F 6, and D–E 15. The cheapest is D–F with 6, so F joins next.
   - board: `add 6`
4. **Pick A–B, then B–E**: With A, D, and F inside, the crossing edges include A–B 7, D–B 9, F–E 8, F–G 11, and D–E 15. The cheapest is A–B 7; after B joins, B–E 7 beats F–E 8 and B–C 8.
   - board: `add 7` · `add 7`
5. **Pick E–C, then E–G**: Now C and G are still outside. The cheapest way to reach C is E–C with 5, and then the cheapest way to reach G is E–G with 9, not F–G 11.
   - board: `add 5` · `add 9`
6. **Final MST and total**: So the edges added in order are A–D, D–F, A–B, B–E, E–C, and E–G. The total is 5 + 6 + 7 + 7 + 5 + 9 = 39.
   - board: `total = 39`
   - sketch: `flowchart TD ; A[Start A] --> B[Choose min crossing] ; B --> C[Add new vertex] ; C --> D[Update crossing edges] ; D -->\|repeat\| B ; D --> E[All vertices reached]`

Missing: skips_cycle_edges: MISSING any: 0 of 4 matched, need 1

## cs_prim_mst, run 2

Question: "Using Prim's algorithm starting from A, which edges are added to the minimum spanning tree, in what order, and what is the total weight?" (cs_prim_mst.png)
Score 4/5 (edges_ad_df_ab PASS, edges_be_ce_eg PASS, prim_order PASS, total_39 PASS, skips_cycle_edges FAIL). Lesson 22.593 s, 8 steps, model gpt-5.5.

**Prim’s Algorithm from A**: We’ll run Prim’s algorithm directly on this weighted graph, starting at A. At each step, we add the cheapest edge that connects the growing tree to a new vertex.

1. **Start the tree at A**: We’re using Prim’s algorithm starting from A, so the tree begins at this A node. From A, only two edges are available: A–D with 5 and A–B with 7.
   - board: `a: start here`
2. **Pick A–D first**: Prim picks the cheapest edge leaving the current tree. Between 5 and 7, choose A–D, so D joins and our running total is 5.
   - board: `a -> d: add 5` · `total = 5`
3. **Pick D–F second**: Now the tree is A and D, so look at edges crossing outward: A–B 7, D–B 9, D–F 6, and D–E 15. The cheapest is D–F with 6, making total 11.
   - board: `d -> f: add 6` · `f: total = 11`
4. **Pick A–B third**: With A, D, and F in the tree, compare the outward edges: A–B 7, D–B 9, D–E 15, F–E 8, and F–G 11. The smallest is A–B, so B joins next and total becomes 18.
   - board: `a -> b: add 7` · `b: total = 18`
5. **Pick B–E fourth**: Now B opens two useful choices: B–E 7 and B–C 8. Against F–E 8, F–G 11, D–B 9, and D–E 15, the cheapest is B–E with 7, so total is 25.
   - board: `b -> e: add 7` · `e: total = 25`
6. **Pick E–C fifth**: The remaining outside vertices are C and G. To reach C, B–C costs 8 but E–C costs 5, so choose E–C and raise the total to 30.
   - board: `e -> c: add 5` · `c: total = 30`
7. **Pick E–G last**: Only G is still outside. The crossing choices are E–G with 9 or F–G with 11, so Prim adds E–G and stops with all seven vertices connected.
   - board: `e -> g: add 9` · `g: all connected`
8. **Final MST order and total**: So the Prim order from A is A–D, D–F, A–B, B–E, E–C, E–G. Add the weights: 5 + 6 + 7 + 7 + 5 + 9 = 39.
   - board: `a+d+f+b+e+c+g: total weight = 39`
   - sketch: `flowchart LR ; A[Start A] --> D[Add min edge] ; D --> F[New vertex] ; F --> B[Update choices] ; B --> E[Repeat min] ; E --> G[All connected]`

Missing: skips_cycle_edges: MISSING any: 0 of 4 matched, need 1

## math_derivative_tangent, run 1

Question: "The curve is f(x) = x² and the tangent touches it at a = 1. How do I find the tangent line y = mx + b?" (math_derivative_tangent.png)
Score 5/5 (point PASS, derivative PASS, slope PASS, intercept PASS, equation PASS). Lesson 16.499 s, 5 steps, model gpt-5.5.

**Tangent Line to f(x)=x² at a=1**: We’ll find the tangent line by using the derivative for the slope, then the point (1, f(1)) to solve for b. The page’s purple line is the tangent form y=mx+b, and the red curve is y=f(x).

1. **Orient: what we’re finding**: We want the purple tangent line to the red curve at a=1. I’m circling the curve, the touch point, and the line formula where our answer will land.
2. **compute the point**: Since f(x)=x² and a=1, the contact point is (1, f(1)). So f(1)=1²=1, meaning the tangent must pass through (1,1).
   - board: `(1,1)` · `f(1)=1`
3. **compute the slope**: The page says the tangent slope is m=f′(a). For f(x)=x², f′(x)=2x, so at a=1 the slope is m=2.
   - board: `m=2` · `sets steepness`
4. **solve for b**: Now plug the point (1,1) and slope 2 into y=mx+b. That gives 1=2·1+b, so b=-1.
   - board: `1=2(1)+b` · `b=-1`
5. **Final answer**: So the tangent line is y=2x−1. The big pattern is: derivative gives slope, the touch point gives b, and together they make the tangent line.
   - board: `y=2x−1`
   - sketch: `flowchart LR ; A[f(x)=x²] --> B[f'(x)=2x] ; B --> C[a=1] ; C --> D[m=2] ; C --> E[(1,1)] ; D --> F[y=2x−1] ; E --> F`

## math_derivative_tangent, run 2

Question: "The curve is f(x) = x² and the tangent touches it at a = 1. How do I find the tangent line y = mx + b?" (math_derivative_tangent.png)
Score 5/5 (point PASS, derivative PASS, slope PASS, intercept PASS, equation PASS). Lesson 16.131 s, 5 steps, model gpt-5.5.

**Tangent Line at a = 1**: We find the tangent to f(x)=x² at a=1 by using the derivative for the slope and the point (a, f(a)) to solve for b. For this graph, the tangent line is y = 2x − 1.

1. **Where the tangent data lives**: We’re finding the purple tangent line to the red curve at a = 1. I’ll circle the touching point first, because every tangent line needs a slope and a point.
2. **Compute the point on f(x)=x²**: At a = 1, plug into the curve: f(1) = 1² = 1. So the tangent must pass through the point (1, 1), the dot I’m labeling.
   - board: `(1,1)` · `x=1 gives y=1`
3. **Use the derivative for slope**: For f(x)=x², the derivative is f′(x)=2x. At a = 1, the slope is m = f′(1) = 2, so the tangent rises 2 for every 1 across.
   - board: `m = 2` · `rise 2`
4. **Solve for b using y=mx+b**: Now use y = mx + b with the point (1,1) and slope m = 2. Substitute carefully: 1 = 2·1 + b, so b = −1.
   - board: `1=2·1+b` · `b = -1`
5. **Final tangent line**: So the tangent line is y = 2x − 1. Big idea: derivative gives the slope, and the touching point gives the intercept.
   - board: `y=2x-1` · `point + slope`
   - sketch: `flowchart LR ; A[Pick a=1] --> B[Find f(1)] ; B --> C[Point (1,1)] ; A --> D[Find f'(1)] ; D --> E[Slope m=2] ; C --> F[Solve b] ; E --> F`

## math_pythagoras, run 1

Question: "How does this picture prove the Pythagorean theorem?" (math_pythagoras_squares.jpg)
Score 2/5 (areas FAIL, sides_3_4_5 FAIL, sum_9_16_25 FAIL, theorem PASS, rearrangement PASS). Lesson 15.319 s, 5 steps, model gpt-5.5.

**Pythagoras by Rearranging Squares**: This picture proves the Pythagorean theorem by building squares on the three sides of a right triangle, then showing the two smaller squares can be cut and rearranged to exactly fill the largest square.

1. **Spot the right triangle**: This picture proves Pythagoras by focusing on the pale green right triangle in the middle. The red square sits on one side, the yellow square sits on another, and the tilted big square sits on the hypotenuse.
2. **Name the three side-squares**: A square drawn on a side has area side squared. So this left red block represents one leg squared, the bottom yellow block represents the other leg squared, and the tilted square represents the hypotenuse squared.
3. **The cut-up pieces match the grid**: Now watch the trick: the red-and-yellow small squares are already chopped into unit grid pieces. Those same colored pieces appear inside the tilted hypotenuse square, just rotated and slid, not stretched.
   - board: `slide/rotate` · `same area` · `no area change`
4. **Why α and β matter**: The angle labels tell us the pieces fit because α plus β makes a right angle. That lets the slanted cuts line up into one straight square boundary around the hypotenuse.
   - board: `α+β=90°`
5. **The area equation**: So the proof is pure area conservation: the two leg-squares on the left and bottom exactly become the one hypotenuse-square. That is why a² plus b² equals c².
   - board: `equal area` · `a²+b²=c²`
   - sketch: `flowchart LR ; A[leg square a²] --> C[cut pieces] ; B[leg square b²] --> C ; C --> D[rearrange] ; D --> E[hypotenuse square c²]`

Missing: areas: MISSING all[1] \| MISSING all[2] \| MISSING all[3]; sides_3_4_5: MISSING any: 0 of 6 matched, need 1; sum_9_16_25: MISSING any: 0 of 5 matched, need 1

## math_pythagoras, run 2

Question: "How does this picture prove the Pythagorean theorem?" (math_pythagoras_squares.jpg)
Score 1/5 (areas FAIL, sides_3_4_5 FAIL, sum_9_16_25 FAIL, theorem PASS, rearrangement FAIL). Lesson 15.354 s, 5 steps, model gpt-5.5.

**Seeing Pythagoras in the Picture**: This diagram proves the Pythagorean theorem by showing that the square on the hypotenuse can be exactly filled by the two squares on the legs. The angle labels explain why the tilted red square fits perfectly between the two leg-squares.

1. **What we’re proving**: Great question: this picture proves Pythagoras by comparing three squares built on the sides of the green right triangle. I’ll circle the triangle first, because everything hangs on its three sides.
   - board: `right triangle`
2. **The two leg-squares**: The horizontal and vertical legs each get their own square: red on the left and yellow below. Their areas are the two addends, so think of them as a² and b².
   - board: `area a²`
3. **The hypotenuse-square**: Now follow the slanted side of the triangle: the big tilted square is built on that hypotenuse. If its side length is c, its area is c².
   - board: `build square` · `area c²`
4. **Why the pieces fit**: The angle labels are the lock: α and β are the two acute angles of the right triangle, so α + β = 90°. That makes the corner between the two leg-squares exactly match the tilted square’s corner.
   - board: `a: α+β=90°`
5. **The area statement**: Here is the proof move: the red area plus the yellow area rearranges to fill the tilted blue square with no gaps or overlaps. So the two leg-square areas equal the hypotenuse-square area.
   - board: `same area` · `same area` · `a²+b²=c²`
   - sketch: `flowchart LR ; A[Leg square a²] --> C[Add areas] ; B[Leg square b²] --> C ; C --> D[Rearrange pieces] ; D --> E[Hypotenuse square c²]`

Missing: areas: MISSING all[1] \| MISSING all[2] \| MISSING all[3]; sides_3_4_5: MISSING any: 0 of 6 matched, need 1; sum_9_16_25: MISSING any: 0 of 5 matched, need 1; rearrangement: MISSING any: 0 of 4 matched, need 1

## math_quadratic, run 1

Question: "Where does this parabola cross the x-axis? Solve its equation step by step." (math_quadratic_roots.png)
Score 5/5 (set_zero PASS, method PASS, root_2 PASS, root_minus_1 PASS, graph_link PASS). Lesson 17.284 s, 5 steps, model gpt-5.5.

**Finding the x-intercepts**: We’ll answer where the red parabola crosses the x-axis by solving the printed equation y = x² − x − 2 with y set to 0. The crossings are the roots, and we can confirm them on the graph.

1. **Aim at the crossings**: We want the x-axis crossings, so I’m circling the equation and the red curve. Crossings happen where the height y becomes zero.
   - board: `y = 0 here`
2. **Turn the graph question into algebra**: At an x-intercept, replace y with 0. So the printed formula becomes a quadratic equation we can solve.
   - board: `set to 0` · `0 = x²−x−2`
3. **Factor the quadratic**: Now we factor x² minus x minus 2. We need two numbers that multiply to −2 and add to −1: that’s −2 and +1.
   - board: `−2×1=−2` · `−2+1=−1` · `0=(x−2)(x+1)`
4. **Use zero-product rule**: If two factors multiply to zero, one factor must be zero. So x−2 equals 0 or x+1 equals 0.
   - board: `x−2=0` · `x+1=0` · `x = 2` · `x = −1`
5. **Match the roots to the graph**: Here are the two answers on the x-axis: the curve crosses at −1 and at 2. So the x-intercepts are the points (−1, 0) and (2, 0).
   - board: `(−1, 0)` · `(2, 0)`
   - sketch: `flowchart TD ; A[Set y=0] --> B[Factor quadratic] ; B --> C[Zero-product rule] ; C --> D[Solve factors] ; D --> E[Plot crossings]`

## math_quadratic, run 2

Question: "Where does this parabola cross the x-axis? Solve its equation step by step." (math_quadratic_roots.png)
Score 5/5 (set_zero PASS, method PASS, root_2 PASS, root_minus_1 PASS, graph_link PASS). Lesson 14.782 s, 5 steps, model gpt-5.5.

**Finding the x-intercepts**: We solve where the parabola crosses the x-axis by setting y = 0 in the displayed equation. Factoring gives the two x-values that match the red curve’s crossings on the graph.

1. **Start at the equation**: We’re finding where this red parabola crosses the x-axis, so the answer lives in the equation and on the horizontal axis. I’ll circle the formula first, then we’ll turn crossing into an algebra problem.
2. **Crossing means y equals zero**: At an x-axis crossing, the height y is exactly 0. So I replace y in the circled equation with 0, giving us the equation to solve.
   - board: `y = 0 here` · `0 = x²−x−2`
3. **Factor the quadratic**: Now we factor x² − x − 2. We need two numbers that multiply to −2 and add to −1: that’s −2 and +1.
   - board: `−2·1=−2` · `−2+1=−1`
4. **Use the zero product property**: So the equation becomes 0 = (x − 2)(x + 1). A product is zero only when one factor is zero, so we solve each small equation.
   - board: `0=(x−2)(x+1)` · `x=2` · `x=−1`
5. **Match the graph crossings**: Here are the two crossings on the red curve: x = −1 and x = 2. That means the parabola crosses the x-axis at the points (−1, 0) and (2, 0).
   - board: `(−1,0), (2,0)`
   - sketch: `flowchart LR ; A[Set y=0] --> B[Factor quadratic] ; B --> C[Set factors zero] ; C --> D[Get x-values] ; D --> E[Plot crossings]`

## math_unit_circle, run 1

Question: "What is sin(150°) and why?" (math_unit_circle.png)
Score 5/5 (value_half PASS, y_coordinate PASS, point_150 PASS, reference_30 PASS, quadrant_sign PASS). Lesson 13.162 s, 5 steps, model gpt-5.5.

**Finding sin(150°) on the Unit Circle**: sin(150°) is the y-coordinate of the point on the unit circle at 150°. Because 150° has a 30° reference angle in Quadrant II, its sine is positive and equals 1/2.

1. **Orient to 150°**: Great question: sin(150°) lives at the 150° ray on this unit circle. I’m circling 150° first, because sine is read from the height of that point.
   - board: `look here`
2. **Use the unit-circle rule**: On the unit circle, each point is written as (cos θ, sin θ). So for 150°, we need the second coordinate—the y-value—beside that dot.
   - board: `(cos, sin)`
3. **Read the coordinate**: Now follow from the 150° dot to its printed coordinate: (-√3/2, 1/2). The sine is the second number, so I’m highlighting 1/2.
   - board: `read point` · `y = sin`
4. **Why it is positive**: Why positive? 150° is in Quadrant II, above the x-axis, so its y-value is positive. Its reference angle is 30°, whose sine is 1/2.
   - board: `above axis` · `positive y`
5. **Final answer**: So the answer is sin(150°) = 1/2. Same height as 30°, but in Quadrant II, where sine stays positive.
   - board: `sin 150° = 1/2`
   - sketch: `flowchart LR ; A[Find 150°] --> B[Read point] ; B --> C[Take y-value] ; C --> D[sin = 1/2]`

## math_unit_circle, run 2

Question: "What is sin(150°) and why?" (math_unit_circle.png)
Score 4/5 (value_half PASS, y_coordinate PASS, point_150 FAIL, reference_30 PASS, quadrant_sign PASS). Lesson 13.796 s, 5 steps, model gpt-5.5.

**Why sin(150°) = 1/2**: On the unit circle, sine is the y-coordinate. Since 150° is in Quadrant II with reference angle 30°, its y-value matches sin(30°), so sin(150°)=1/2.

1. **Find the angle on the circle**: We’re answering: what is sin(150°)? I’ll circle the 150° ray because the sine value lives at the point where this ray hits the unit circle.
2. **Sine means y-coordinate**: On this chart, each outside ordered pair is (cos θ, sin θ). So for 150°, we only need the second coordinate—the height above the x-axis.
   - board: `(cos, sin)` · `read point`
3. **Use the reference angle**: Now look: 150° is 30° short of 180°, so its reference angle is 30°. That means its height matches the 30° point, just mirrored to the left.
   - board: `180−150=30°`
4. **Read the matching height**: At 30°, the point is labeled with y-coordinate 1/2. Mirroring into Quadrant II keeps the same height, so the sine stays positive 1/2.
   - board: `same height`
5. **Final answer**: So the answer is sin(150°)=1/2. Big idea: sine is height on the unit circle, and 150° has the same height as 30° in Quadrant II.
   - board: `sin=1/2`
   - sketch: `flowchart LR ; A[150° angle] --> B[Reference 30°] ; B --> C[Same height] ; C --> D[Quadrant II] ; D --> E[sin positive] ; E --> F[sin = 1/2]`

Missing: point_150: MISSING any: 0 of 3 matched, need 1

## cs_gbn_vs_sr, run 1

Question: "In both timelines frame 2 is damaged. What does the receiver do with the frames that arrive after it, and which frames does the sender retransmit, in (a) Go-Back-N versus (b) Selective Repeat?" (cs_gbn_vs_sr.png)
Score 4/5 (gbn_discards_3_to_8 PASS, gbn_timeout_resends_from_2 PASS, sr_buffers_3_to_5 PASS, sr_nak_only_2 PASS, sr_ack_5 FAIL). Lesson 18.856 s, 6 steps, model gpt-5.5.

**Frame 2 Error: Go-Back-N vs Selective Repeat**: The page compares what happens after frame 2 is damaged in two sliding-window protocols. Go-Back-N discards later frames and retransmits a whole run; Selective Repeat buffers later frames and retransmits only the missing damaged frame.

1. **Orient: the same error, two policies**: We’re answering your frame 2 question by comparing the top timeline, Go-Back-N, with the bottom timeline, Selective Repeat. I’ll circle the damaged spot in both: same error, different receiver behavior.
   - board: `Go-Back-N` · `Selective Repeat`
2. **Go-Back-N receiver discards later frames**: In the top case, after frame 2 is damaged, the receiver is still waiting for 2. So frames 3 through 8 arrive out of order and get thrown away by the data link layer.
   - board: `d: not delivered`
3. **Go-Back-N sender retransmits from 2 onward**: When the timeout interval ends, the sender goes back to the missing frame 2. Follow my blue box: it retransmits 2, then 3, 4, 5, 6, 7, and 8 before continuing with 9.
   - board: `timeout`
4. **Selective Repeat receiver buffers later frames**: Now the bottom case: frame 2 is still the hole, but the receiver accepts good later frames. Frames 3, 4, and 5 are buffered instead of discarded, waiting until 2 is repaired.
   - board: `kept safe`
5. **Selective Repeat retransmits only frame 2**: The NAK points exactly at the missing frame, so Selective Repeat resends only frame 2. Once that 2 arrives, the buffered 3, 4, and 5 can be delivered in order.
   - board: `resend 2`
6. **Answer recap**: So the answer is: Go-Back-N discards everything after damaged 2 and retransmits 2 through 8 here. Selective Repeat buffers later good frames and retransmits only 2.
   - sketch: `flowchart TD ; A[Frame 2 damaged] ; B{Protocol?} ; C[Go-Back-N] ; D[Discard later] ; E[Retransmit 2-8] ; F[Selective Repeat] ; G[Buffer later] ; H[Retransmit 2] ; A --> B ; B --> C ; C --> D ; D --> E ; B --> F ; F --> G ; G --> H`

Missing: sr_ack_5: MISSING any: 0 of 5 matched, need 1

## cs_gbn_vs_sr, run 2

Question: "In both timelines frame 2 is damaged. What does the receiver do with the frames that arrive after it, and which frames does the sender retransmit, in (a) Go-Back-N versus (b) Selective Repeat?" (cs_gbn_vs_sr.png)
Score 4/5 (gbn_discards_3_to_8 PASS, gbn_timeout_resends_from_2 PASS, sr_buffers_3_to_5 PASS, sr_nak_only_2 PASS, sr_ack_5 FAIL). Lesson 19.677 s, 6 steps, model gpt-5.5.

**Damaged Frame 2: Go-Back-N vs Selective Repeat**: Both timelines show frame 2 getting an error. In Go-Back-N the receiver discards later out-of-order frames and the sender retransmits from 2 onward; in Selective Repeat the receiver buffers later good frames and the sender retransmits only frame 2.

1. **Find the damaged frame**: Great question—both diagrams start the same: frame 2 is the trouble spot. I’m circling the error in each timeline, because everything after it shows the protocol difference.
   - board: `frame 2 damaged`
2. **Go-Back-N receiver behavior**: In Go-Back-N, once frame 2 is damaged, the receiver refuses later frames 3 through 8 because they are out of order. These D marks mean discarded, not saved.
   - board: `d: not buffered`
3. **Go-Back-N sender retransmits a block**: Now follow the timeout: because ACK 2 never arrives, the sender goes back to frame 2. So in part (a), it retransmits 2, 3, 4, 5, 6, 7, 8, and then continues with 9.
   - board: `go back`
4. **Selective Repeat receiver behavior**: In Selective Repeat, the receiver still notices frame 2 is missing, but it keeps later correct frames. That buffered group is frames 3, 4, and 5 waiting until 2 is resent.
   - board: `saved out-of-order`
5. **Selective Repeat sender retransmits only the missing one**: Here the NAK 2 pinpoints exactly what failed, so the sender retransmits only frame 2. After that, the receiver can deliver buffered 3, 4, and 5 in order, then continue normally.
   - board: `only 2` · `then in order`
6. **Plain answer**: So the answer is: Go-Back-N discards frames after damaged 2 and retransmits the whole run from 2. Selective Repeat buffers good later frames and retransmits only damaged 2.
   - sketch: `flowchart LR ; A[Frame 2 damaged] --> B{Protocol?} ; B --> C[Go-Back-N] ; C --> D[Discard later] ; C --> E[Retransmit 2 onward] ; B --> F[Selective Repeat] ; F --> G[Buffer later] ; F --> H[Retransmit only 2]`

Missing: sr_ack_5: MISSING any: 0 of 5 matched, need 1

## cs_tcp_handshake, run 1

Question: "Walk me through this TCP three-way handshake: what do the SYN, Seq and Ack values in each of the three segments mean, and why is the first acknowledgement number 1024?" (cs_tcp_handshake.png)
Score 5/5 (client_syn_1023 PASS, server_isn_2131691 PASS, ack_1024_is_1023_plus_1 PASS, final_ack_2131692 PASS, third_seq_1024_established PASS). Lesson 19.533 s, 6 steps, model gpt-5.5.

**TCP Three-Way Handshake Values**: This diagram shows how client A and server B open a TCP connection using SYN, sequence numbers, and acknowledgements. The key idea: a SYN consumes one sequence number, so acknowledging Seq 1023 means sending Ack Number 1024.

1. **Orient: the handshake over time**: We’re walking down time, so the three slanted boxes are the three TCP segments. I’ll circle client A and server B, then we’ll read each segment in order.
   - board: `later`
2. **Segment 1: A chooses its starting number**: First, A sends a SYN with Seq 1023. SYN means ‘please open a connection,’ and Seq 1023 is A’s initial sequence number, not data bytes yet.
   - board: `SYN` · `A ISN = 1023`
3. **Why the first acknowledgement is 1024**: Here’s the crucial rule: a SYN uses up one sequence number. So B has received A’s 1023 and now expects A’s next number, 1024.
   - board: `1023 + 1`
4. **Segment 2: B replies and announces its own number**: Now B replies with SYN=1 and ACK=1. That single segment both acknowledges A, and starts B’s side with its own Seq 2131691.
   - board: `B ISN = 2131691`
5. **Segment 3: A acknowledges B’s SYN**: Finally A sends ACK=1 with SYN=0, because the connection request part is finished. Its Seq is 1024, and it acknowledges B’s SYN by sending Ack Number 2131692.
   - board: `2131691 + 1`
6. **Recap: SYN consumes one count**: So the answer is: each side picks an initial Seq, and the other side’s Ack Number means ‘next byte I expect.’ The first acknowledgement is 1024 because A’s SYN at 1023 consumes one sequence number.
   - board: `next expected`
   - sketch: `flowchart TD ; A[A sends SYN] --> B[B ACKs 1024] ; B --> C[B sends SYN] ; C --> D[A ACKs 2131692] ; D --> E[Connection open]`

## cs_tcp_handshake, run 2

Question: "Walk me through this TCP three-way handshake: what do the SYN, Seq and Ack values in each of the three segments mean, and why is the first acknowledgement number 1024?" (cs_tcp_handshake.png)
Score 5/5 (client_syn_1023 PASS, server_isn_2131691 PASS, ack_1024_is_1023_plus_1 PASS, final_ack_2131692 PASS, third_seq_1024_established PASS). Lesson 17.933 s, 6 steps, model gpt-5.5.

**TCP Three-Way Handshake Values**: This diagram shows TCP connection setup between client A and server B. The key idea: SYN consumes one sequence number, so each side acknowledges the other side’s initial sequence number plus 1.

1. **Orient: three messages set up one TCP connection**: We’re walking down time through this three-way handshake: client A starts, server B replies, then A confirms. I’ll circle the three segments we need and keep the sequence numbers in blue.
2. **Segment 1: A sends SYN with its starting Seq**: First, A sends SYN=1, meaning “please open a connection.” Its Seq is 1023: that is A’s chosen starting sequence number, and ACK=0 because A has not received B’s sequence yet.
   - board: `A starts at 1023`
3. **Segment 2: B acknowledges A’s SYN and sends its own SYN**: Now B replies with SYN=1 and ACK=1, so this one segment does two jobs. Its Seq is 2131691, while Ack Number is 1024 because B expects A’s next byte: 1023 plus one for the SYN.
4. **Why 1024: SYN uses one sequence number**: Here’s the arithmetic: a SYN flag consumes one sequence number even though it carries no data byte. So B acknowledges A’s SYN as 1023 → next expected 1024.
   - board: `+1 for SYN` · `1023 + 1`
5. **Segment 3: A acknowledges B’s SYN and may send data**: Finally A sends SYN=0 because it is no longer asking to open; the connection is being confirmed. Its Seq is 1024, and its Ack Number is 2131692: B’s starting Seq 2131691 plus one for B’s SYN.
   - board: `+1 for SYN`
6. **Recap: each side says “next number I expect”**: So the answer is: Ack is not echoing the received Seq; it names the next sequence number expected. That is why the first acknowledgement is 1024, not 1023.
   - board: `next expected`
   - sketch: `flowchart TD ; A[A SYN Seq 1023] --> B[B ACK 1024] ; B --> C[B SYN Seq 2131691] ; C --> D[A ACK 2131692] ; D --> E[Connection established]`

## cs_deadlock_rag, run 1

Question: "Is there a deadlock in this resource-allocation graph? R3 has two instances, so does the cycle really mean deadlock?" (cs_deadlock_rag.png)
Score 4/5 (p1_holds_r3_waits_r1 PASS, p2_holds_r1_waits_r2 PASS, p3_holds_r2_waits_r3 PASS, cycle FAIL, deadlock_because_no_free_instance PASS). Lesson 18.148 s, 6 steps, model gpt-5.5.

**Deadlock with Multi-Instance R3**: This resource-allocation graph has a cycle, but because R3 has two instances we must simulate whether any process can finish and release resources. Here, the cycle really does imply deadlock for P1, P2, and P3 because no needed R3 instance can be freed.

1. **Locate the possible deadlock**: Great question: R3 has two dots, so a cycle alone is not always enough. I’ll circle the cycle suspects, then we’ll test whether anyone can actually finish.
2. **Read what is allocated**: Solid dots inside boxes are resource instances, and an arrow from a dot to a process means allocated. So P1 owns one R3, P2 owns R1, and P3 owns one R2.
   - board: `allocated` · `allocated` · `allocated`
3. **Read what is being requested**: Now the process-to-resource arrows are requests. P1 is waiting for R1, P2 is waiting for R2 and R3, and P3 is waiting for R3.
   - board: `requests` · `requests` · `requests`
4. **Test R3’s two instances**: Here is the key point: R3 has two instances, but both are already allocated. One goes to P1, and the other goes to P2, so P3 cannot grab a free R3.
   - board: `available = 0` · `allocated`
5. **Try to finish a process**: To break deadlock, some process must get all its requests and finish. But P1 needs R1 held by P2, P2 needs R2 held by P3 and R3, and P3 needs R3 with none free.
   - board: `blocked: needs R1` · `blocked: needs R2,R3` · `blocked: needs R3`
6. **Answer: yes, deadlock**: So yes: this graph is deadlocked, even though R3 has two instances. Multi-instance resources make a cycle only a warning, but here the availability test confirms nobody can finish.
   - board: `deadlock confirmed`
   - sketch: `flowchart TD ; A[Count available] ; B[Find finishable process] ; C[Release its resources] ; D[Repeat] ; E[None finishable] ; F[Deadlock] ; A --> B ; B -->\|yes\| C ; C --> D ; D --> B ; B -->\|no\| E ; E --> F`

Missing: cycle: cycl \| MISSING any: 0 of 13 matched, need 1

## cs_deadlock_rag, run 2

Question: "Is there a deadlock in this resource-allocation graph? R3 has two instances, so does the cycle really mean deadlock?" (cs_deadlock_rag.png)
Score 1/5 (p1_holds_r3_waits_r1 PASS, p2_holds_r1_waits_r2 FAIL, p3_holds_r2_waits_r3 FAIL, cycle FAIL, deadlock_because_no_free_instance FAIL). Lesson 18.761 s, 6 steps, model gpt-5.5.

**Deadlock Check with Multi-Instance R3**: This resource-allocation graph has a cycle involving P1, R1, P2, R3, and P1, but because R3 has two instances we must simulate availability, not assume deadlock from the cycle alone.

1. **Orient: cycle is only a warning**: We’re checking whether this graph is deadlocked. I’ll circle the resource boxes and the processes first: with multiple instances, a cycle is suspicious, not automatic proof.
   - board: `2 instances`
2. **Read allocations and requests**: Now follow arrow direction carefully. A resource-to-process arrow means held; a process-to-resource arrow means waiting for that resource.
   - board: `held by` · `requests` · `held by`
3. **Spot the visible cycle**: Here is the cycle people notice: P1 waits for R1, R1 is held by P2, P2 waits for R3, and R3 is held by P1. If every needed instance were unavailable forever, that would trap them.
   - board: `waits` · `waits`
4. **Simulate the escape through R3**: But R3 has two instances, so count them. One R3 dot is allocated to P1, while the other R3 dot is allocated to P3; if P3 can finish, it releases R3 and gives P2 a way out.
   - board: `can release`
5. **Release chain breaks the cycle**: After P3 releases R3, P2 can get that R3 instance and finish. Then P2 releases R1, so P1 can get R1; the waiting loop is broken.
   - board: `free after P3` · `grant` · `then grant`
   - sketch: `flowchart TD ; A[P3 finishes] ; B[Free R3] ; C[P2 gets R3] ; D[P2 finishes] ; E[Free R1] ; F[P1 gets R1] ; A-->B ; B-->C ; C-->D ; D-->E ; E-->F`
6. **Answer: cycle, but no deadlock shown**: So the answer is: the cycle does not prove deadlock here. Because R3 has two instances and P3 can release one, this graph is not deadlocked as drawn.
   - board: `not deadlock`

Missing: p2_holds_r1_waits_r2: r1, r1 is held by p2 \| MISSING all[2]; p3_holds_r2_waits_r3: MISSING all[1] \| MISSING all[2]; cycle: cycl \| MISSING any: 0 of 13 matched, need 1; deadlock_because_no_free_instance: deadlocked \| MISSING any: 0 of 6 matched, need 1

## cs_lru_cache, run 1

Question: "This LRU example has 4 slots and the access sequence A B C D E D F (the number in brackets is the time of last use). Why does E replace A, why does F replace B, and how many hits and misses are there?" (cs_lru_cache.png)
Score 5/5 (e_evicts_a PASS, d_hit_updated PASS, f_evicts_b PASS, six_misses PASS, one_hit PASS). Lesson 17.939 s, 6 steps, model gpt-5.5.

**LRU with 4 Slots: E Replaces A, F Replaces B**: We simulate the access sequence A B C D E D F using Least Recently Used replacement. The bracketed number is the last-use time, so the smallest number is evicted when all 4 slots are full.

1. **Orient: what the boxes show**: This page is an LRU cache trace with four slots. I’ll circle the full cache right before the first replacement: A, B, C, D with last-use times 0, 1, 2, 3.
   - board: `4 slots filled`
2. **Build the first four accesses**: A, B, C, and D are all first-time accesses, so each is a miss and simply fills the next empty slot. After D, the cache is full, so the next miss must evict someone.
   - board: `B miss` · `C miss` · `D miss`
3. **Why E replaces A**: Now E is accessed, but E is not in the full cache: miss. LRU evicts the smallest last-use time, and A has 0, so E replaces A at time 4.
   - board: `evict LRU` · `miss #5`
4. **Why D changes from 3 to 5**: Next the sequence accesses D again. D is already in the cache, so that is a hit, and only D’s last-use time updates from 3 to 5.
   - board: `hit: update` · `hit #1`
5. **Why F replaces B**: Then F is accessed, and F is not in the cache: another miss. Among E(4), B(1), C(2), and D(5), B has the smallest time, so F replaces B at time 6.
   - board: `evict LRU` · `miss #6`
6. **Final count**: So the full sequence A B C D E D F has six misses and one hit. The big rule is: on a miss, replace the cached item with the smallest bracketed time.
   - board: `Hits=1, Misses=6`
   - sketch: `flowchart LR ; A[Access item] --> B{In cache?} ; B -->\|yes\| C[Hit] ; C --> D[Update time] ; B -->\|no\| E[Miss] ; E --> F[Evict oldest] ; F --> D`

## cs_lru_cache, run 2

Question: "This LRU example has 4 slots and the access sequence A B C D E D F (the number in brackets is the time of last use). Why does E replace A, why does F replace B, and how many hits and misses are there?" (cs_lru_cache.png)
Score 5/5 (e_evicts_a PASS, d_hit_updated PASS, f_evicts_b PASS, six_misses PASS, one_hit PASS). Lesson 18.364 s, 6 steps, model gpt-5.5.

**LRU with 4 Slots: Hits, Misses, Replacements**: We simulate the access sequence A B C D E D F. LRU evicts the page with the smallest bracket number, because that page was used least recently.

1. **Set up the LRU rule**: This page is tracing LRU for four slots: the bracket is the time of last use. We’ll follow the sequence A, B, C, D, E, D, F and always replace the smallest time.
   - board: `time stamp`
2. **Fill the empty frames: A, B, C, D**: The first four requests go into empty slots, so each one is a miss. After D arrives, the cache is full: A0, B1, C2, D3.
   - board: `miss, add B` · `miss, add C`
3. **Why E replaces A**: Now E is requested, but E is not in the full cache, so it’s a miss. LRU compares the times 0, 1, 2, 3; A has the smallest time, so E replaces A.
   - board: `oldest: 0` · `replace`
4. **D is a hit, so update its time**: Next request is D, and D is already there, so this is a hit. We do not replace anything; we only update D’s last-use time from 3 to 5.
   - board: `hit: 3→5` · `1 hit`
5. **Why F replaces B**: Finally F is requested, and F is not in the cache, so it’s another miss. Among E4, B1, C2, D5, the smallest time is B1, so F replaces B.
   - board: `replace`
6. **Count the hits and misses**: So the answer is: E replaces A because A has the oldest time 0; F replaces B because B has the oldest time 1. Counts: A, B, C, D, E, F are misses, and only the second D is a hit.
   - board: `Hits=1, Misses=6`
   - sketch: `flowchart LR ; A[Request page] --> B{In cache?} ; B -->\|yes\| C[Hit] ; C --> D[Update time] ; B -->\|no\| E[Miss] ; E --> F[Evict oldest] ; F --> D`

## cs_sjf_gantt, run 1

Question: "This chart shows non-preemptive Shortest Job First. Why do P9, P8 and P7 run in that order, why does P12 wait so long, and what is the average waiting time?" (cs_sjf_gantt.png)
Score 2/5 (order_p9_p8_p7 PASS, waits_p7_p8_p9 FAIL, p12_waits_8 PASS, total_33 FAIL, average_2_36 FAIL). Lesson 19.687 s, 6 steps, model gpt-5.5.

**Non-preemptive SJF on the Gantt chart**: This chart schedules jobs by non-preemptive Shortest Job First: whenever the CPU becomes free, choose the arrived process with the smallest burst time. We will trace the key decisions and compute the average waiting time from the gray bars.

1. **Orient: gray waits, black runs**: This page is a non-preemptive SJF timeline: gray means waiting, black means running. The answer lives in the black bars and the gray waiting bars beside each process.
   - board: `not using CPU`
2. **Why P9, then P8, then P7**: At time 7, P7, P8, and P9 all have arrived, so SJF compares burst lengths. The shortest burst is P9=1, then P8=2, then P7=3, so the black bars run in that order.
   - board: `next shortest` · `last of three`
3. **P12 waits because SJF is non-preemptive**: Now look at time 13: P10, P11, and P12 arrive together, and SJF starts with the shortest, P10. When P13 and P14 arrive at 17, they are shorter than P12, so P12 keeps waiting until time 21.
   - board: `wait = 8`
4. **Read every waiting time**: For average waiting time, measure each gray bar from arrival to its black bar. I’ll write the waits beside the rows: they add to 47 time units across 14 processes.
   - board: `w=0` · `w=1` · `w=2` · `w=5`
5. **Finish the average**: Here is the whole sum: 0+1+2+0+1+3+5+3+2+1+3+8+1+2 = 32? Wait, reading the chart correctly gives total 32, so the average is 32 divided by 14, about 2.29.
   - board: `Σwait=32` · `avg=32/14=2.29`
   - sketch: `flowchart TD ; A[CPU free] ; B[Arrived jobs] ; C[Pick shortest] ; D[Run to finish] ; E[Record wait] ; A-->B ; B-->C ; C-->D ; D-->E ; E-->A`
6. **Answer recap**: So P9, P8, P7 run shortest-to-longest among the jobs available at time 7. P12 waits 8 units because shorter later arrivals run before it, and the average waiting time is about 2.29.
   - board: `SJF choice`

Missing: waits_p7_p8_p9: MISSING all[1] \| MISSING all[2] \| MISSING all[3]; total_33: MISSING any: 0 of 1 matched, need 1; average_2_36: MISSING any: 0 of 3 matched, need 1

## cs_sjf_gantt, run 2

Question: "This chart shows non-preemptive Shortest Job First. Why do P9, P8 and P7 run in that order, why does P12 wait so long, and what is the average waiting time?" (cs_sjf_gantt.png)
Score 1/5 (order_p9_p8_p7 PASS, waits_p7_p8_p9 FAIL, p12_waits_8 FAIL, total_33 FAIL, average_2_36 FAIL). Lesson 18.837 s, 6 steps, model gpt-5.5.

**Non-preemptive SJF on the timeline**: This chart is a non-preemptive Shortest Job First schedule: whenever the CPU becomes free, it chooses the shortest burst among processes that have already arrived. We’ll trace the choices around P9/P8/P7, explain P12’s long wait, then compute the average waiting time from the bars.

1. **Orient to the SJF timeline**: We’re reading this as non-preemptive SJF: the gray bar is waiting, and the black bar is the actual CPU burst. The answer lives in the order of these black bars along the time ruler.
2. **Why P9, then P8, then P7?**: At time 7, P7, P8, and P9 have all arrived, so SJF compares only their burst lengths: 3, 2, and 1. The shortest is P9, then after it finishes, P8 is shorter than P7.
   - board: `1: shortest` · `2 next` · `3 last`
3. **Simulate the choices at time 7**: Follow my arrows: P9 runs from 9 to 10, then P8 runs from 10 to 12, then P7 runs from 12 to 15. Non-preemptive means once each black bar starts, it keeps the CPU until finished.
   - board: `then` · `then` · `wait 7→12 = 5`
4. **Why P12 waits so long**: Now look at time 13: P10, P11, and P12 arrive together, but SJF chooses burst 1, then burst 2, before burst 3. So P12 waits while P10 and P11 run first.
   - board: `1 first` · `2 second` · `wait 13→21 = 8`
5. **Compute every waiting time**: Let’s total the gray bars: waiting time is start time minus arrival time. From the chart we get 0, 1, 2, 0, 1, 3, 5, 3, 2, 1, 2, 8, 1, 2, which sum to 31.
   - board: `total wait = 31` · `14 processes`
6. **Average waiting time answer**: So the average waiting time is 31 divided by 14, which is about 2.21 time units. Big idea: at each decision point, non-preemptive SJF picks the shortest available job and never interrupts it.
   - board: `31/14 ≈ 2.21`
   - sketch: `flowchart LR ; A[CPU free] --> B[Find arrived] ; B --> C[Pick shortest] ; C --> D[Run to finish] ; D --> E[Repeat] ; E -->\|all done\| F[Average waits]`

Missing: waits_p7_p8_p9: MISSING all[1] \| MISSING all[2] \| MISSING all[3]; p12_waits_8: MISSING all[1] \| shorter; total_33: MISSING any: 0 of 1 matched, need 1; average_2_36: MISSING any: 0 of 3 matched, need 1

## math_kinematics, run 1

Question: "For the example at the bottom, how far does the object travel in the 5 seconds? Check it with the v–t graph." (math_kinematics_slide.png)
Score 4/5 (formula FAIL, substitution PASS, final_velocity PASS, distance_25 PASS, graph_area PASS). Lesson 14.73 s, 6 steps, model gpt-5.5.

**Finding Distance from Constant Acceleration**: We use the example values u = 0, a = 2 m/s², and t = 5 s to find displacement. Then we check the same answer as the area under the velocity–time graph.

1. **Where the answer lives**: Great question! The distance comes from displacement, so I’m circling the example and the area-under-the-graph idea that checks it.
2. **Choose the displacement formula**: Since the question asks how far, we want s, not just final velocity. I’m boxing the formula that gives displacement directly from u, a, and t.
   - board: `distance formula`
3. **Substitute the example numbers**: Now plug in the example: u is zero, acceleration is 2, and time is 5. So s = 0×5 + 1/2×2×5².
4. **Compute the displacement**: Let’s simplify it: the first term disappears because u = 0. The second term is 1×25, so the displacement is 25 metres.
   - board: `s = 25 m` · `plug in`
5. **Check with the v–t graph area**: Now check the graph: displacement is area under velocity versus time. Starting from rest makes this shaded shape a triangle with base 5 s and height 10 m/s.
   - board: `base = 5 s` · `height = 10 m/s`
6. **Final answer**: Triangle area is 1/2×base×height = 1/2×5×10 = 25. So yes—the object travels 25 m in the 5 seconds.
   - board: `area = 25 m`
   - sketch: `flowchart LR ; A[Use example] --> B[Choose s formula] ; B --> C[Compute 25 m] ; C --> D[Check graph area] ; D --> E[Same answer]`

Missing: formula: MISSING any: 0 of 3 matched, need 1

## math_kinematics, run 2

Question: "For the example at the bottom, how far does the object travel in the 5 seconds? Check it with the v–t graph." (math_kinematics_slide.png)
Score 5/5 (formula PASS, substitution PASS, final_velocity PASS, distance_25 PASS, graph_area PASS). Lesson 13.363 s, 5 steps, model gpt-5.5.

**Distance in 5 Seconds**: We use the constant-acceleration displacement equation, then check the same distance as the area under the velocity–time graph. For the example, the object travels 25 m.

1. **Find the example and the distance tool**: We’re answering: how far in these 5 seconds? I’ll circle the bottom example, then the displacement equation that matches distance.
2. **Substitute the given values**: The example gives u = 0, a = 2, and t = 5. Watch those drop straight into s = ut + ½at².
   - board: `s=0·5+½·2·5²`
3. **Compute the displacement**: Now calculate it: the first term is zero, and the acceleration term is 25. So the equation says s = 25 m.
   - board: `0 + 25` · `s = 25 m`
4. **Check with the v–t graph area**: Now the graph check: displacement is area under the v–t line. Starting from rest and ending at 10 m/s over 5 s makes a triangle: ½ × base × height.
   - board: `t: base = 5 s` · `height = 10 m/s`
5. **Same answer both ways**: The area check gives ½ × 5 × 10 = 25 m, exactly the same. So the object travels 25 metres in the 5 seconds.
   - board: `½·5·10=25 m`
   - sketch: `flowchart LR ; A[Given u,a,t] --> B[Find final v] ; B --> C[v-t triangle] ; C --> D[Area = distance] ; D --> E[25 m]`

## math_ohm_internal_resistance, run 1

Question: "How do we get the 1.5 A current and the 7.5 V across R in this circuit?" (math_ohm_internal_resistance.jpg)
Score 5/5 (total_resistance PASS, current PASS, internal_drop PASS, terminal_voltage PASS, kirchhoff PASS). Lesson 16.595 s, 6 steps, model gpt-5.5.

**Finding the Current and R Voltage**: The circuit uses a 12 V source with internal resistance 3 Ω in series with an external resistor 5 Ω. The current is the emf divided by the total series resistance, then the voltage across R is found with Ohm’s law.

1. **Where the answer lives**: We’re answering your question right here: this series circuit makes the 1.5 A current, and that same current gives the 7.5 V across R. I’ll circle the two results first.
2. **Total resistance in series**: The battery’s internal resistance r and the outside resistor R are in one loop, so the current has to pass through both. Series resistances add: 3 Ω plus 5 Ω gives 8 Ω total.
   - board: `3+5=8 Ω`
3. **Use emf over total resistance**: Now the source pushes with ε = 12 V across the whole series path. So Ohm’s law for the whole loop is I = 12 V divided by 8 Ω, which gives 1.5 A.
   - board: `÷ 8 Ω` · `I=1.5 A`
4. **Voltage across the external resistor**: For the voltage across R only, use only the 5 Ω resistor. The same series current flows through it, so IR = 1.5 A times 5 Ω equals 7.5 V.
   - board: `× 5 Ω` · `1.5×5=7.5`
5. **Check with the internal drop**: The graph also checks the missing voltage: inside the battery, the internal resistor drops Ir = 4.5 V. Together, 4.5 V plus 7.5 V uses up the full 12 V.
   - board: `1.5×3=4.5` · `4.5+7.5=12`
6. **Answer in one chain**: So the recipe is: add series resistances, find the loop current, then multiply by R for the terminal voltage. That is why this page shows 1.5 A and IR = 7.5 V.
   - sketch: `flowchart LR ; A[12 V emf] --> B[3+5 ohm] ; B --> C[I=1.5 A] ; C --> D[V_R=IR] ; D --> E[7.5 V]`

## math_ohm_internal_resistance, run 2

Question: "How do we get the 1.5 A current and the 7.5 V across R in this circuit?" (math_ohm_internal_resistance.jpg)
Score 5/5 (total_resistance PASS, current PASS, internal_drop PASS, terminal_voltage PASS, kirchhoff PASS). Lesson 18.766 s, 6 steps, model gpt-5.5.

**Finding Current and Voltage Across R**: This circuit has a 12 V source with two series resistances: internal resistance r = 3 Ω and external resistor R = 5 Ω. The current is found from total series resistance, then the voltage across R is IR.

1. **Where the answer lives**: Great question — the 1.5 A comes from treating r and R as series resistors, and the 7.5 V is the drop across R. I’ll circle the two resistors and the current label we’re trying to justify.
2. **Add the series resistances**: Because there is only one loop, the same current must pass through r and R. So we first add their resistances: 3 ohms plus 5 ohms gives 8 ohms total.
   - board: `3+5=8 Ω`
3. **Use Ohm’s law for the loop**: Now use the battery voltage: current equals voltage divided by total resistance. So 12 volts divided by 8 ohms gives 1.5 amps — that matches the red arrow.
   - board: `I=12/8=1.5 A` · `Ohm’s law`
4. **Find voltage across R**: For the external resistor R, use only its own resistance: V_R equals I times R. The same 1.5 amps through 5 ohms gives 7.5 volts, which is the IR drop shown on the graph.
   - board: `V=1.5×5=7.5 V`
5. **Connect to the voltage graph**: The graph is showing the same energy drops around the loop: start at 12 V, lose 4.5 V in the internal resistance, then lose 7.5 V in R. Those two drops add back to the battery’s 12 V.
6. **Plain answer**: So the answer is: total resistance is 8 ohms, so I = 12/8 = 1.5 A; across R, V = IR = 1.5×5 = 7.5 V. Follow this little flow whenever a battery has internal resistance in series.
   - sketch: `flowchart LR ; A[12 V source] --> B[Add resistors] ; B --> C[8 ohms total] ; C --> D[I = V/R] ; D --> E[1.5 A] ; E --> F[VR = IR] ; F --> G[7.5 V]`

## math_parallel_meters, run 1

Question: "Suppose the battery gives 12 V, R1 = 4 Ω, R2 = 2 Ω and R3 = 4 Ω. What do the ammeters A1, A2, A3 and the voltmeters V3 and V4 read?" (math_parallel_meters.png)
Score 5/5 (topology PASS, a2_r1_branch PASS, a3_r2r3_branch PASS, a1_total PASS, v3_v4_split PASS). Lesson 17.275 s, 6 steps, model gpt-5.5.

**Circuit Meter Readings**: The circuit has one 12 V supply feeding two parallel branches: R1 alone, and R2 plus R3 in series. We compute branch currents first, then split the voltage across R2 and R3 to get V3 and V4.

1. **Find the circuit structure**: We need the readings, so first circle the 12 V source and the two paths it feeds. The top-middle path has R1; the bottom path has R2 then R3 in series.
2. **Use parallel-branch voltage**: Both branches connect across the same two side rails, so each branch gets the full 12 V. That means R1 has 12 V, and the series pair R2 plus R3 also has 12 V.
   - board: `12 V` · `12 V` · `12 V`
3. **Compute A2 through R1**: Now the R1 branch current is Ohm’s law: 12 divided by 4 gives 3 A. So the ammeter sitting in that branch, A2, reads 3 A.
   - board: `12/4 = 3 A` · `3 A`
4. **Compute A3 through the lower branch**: For the lower branch, R2 and R3 add because they are in series: 2 plus 4 is 6 ohms. The branch current is 12 divided by 6, so A3 reads 2 A.
   - board: `2+4=6 Ω` · `12/6 = 2 A`
5. **Add currents for A1**: A1 is before the split, so it measures the total current from the battery. Add the two branch currents: 3 A plus 2 A equals 5 A.
   - board: `3 A` · `2 A` · `3+2=5 A`
6. **Split voltage across R2 and R3**: Last, voltmeters V3 and V4 read the drops across R2 and R3. The same 2 A flows through both lower resistors, so V3 is 2×2 = 4 V and V4 is 2×4 = 8 V.
   - board: `2×2=4 V` · `2×4=8 V`
   - sketch: `flowchart TD ; A[12 V supply] --> B[Parallel split] ; B --> C[R1: 4 ohm] ; B --> D[R2+R3: 6 ohm] ; C --> E[A2 = 3 A] ; D --> F[A3 = 2 A] ; E --> G[A1 = 5 A] ; F --> G`

## math_parallel_meters, run 2

Question: "Suppose the battery gives 12 V, R1 = 4 Ω, R2 = 2 Ω and R3 = 4 Ω. What do the ammeters A1, A2, A3 and the voltmeters V3 and V4 read?" (math_parallel_meters.png)
Score 5/5 (topology PASS, a2_r1_branch PASS, a3_r2r3_branch PASS, a1_total PASS, v3_v4_split PASS). Lesson 19.713 s, 6 steps, model gpt-5.5.

**Circuit Readings from a 12 V Battery**: This circuit has one 12 V source feeding two parallel branches: R1 alone, and R2–R3 in series. We compute branch currents and voltage drops, then match them to A1, A2, A3, V3, and V4.

1. **Find the two branches**: We’re answering the meter readings by first seeing the layout: the 12 V battery feeds two parallel paths. I’ll circle the source, then box the R1 branch and the lower R2–R3 branch.
2. **Use parallel voltage**: Because each branch connects across the same left and right rails, each branch gets the full 12 V. So R1 has 12 V, and the series pair R2 plus R3 also has 12 V total.
   - board: `12 V across` · `12 V total` · `parallel: same V`
3. **Compute current through R1**: Now run Ohm’s law on the upper resistor: I equals V over R, so 12 divided by 4 is 3 A. That means A2 reads 3 A in the R1 branch.
   - board: `12/4 = 3 A` · `A2 = 3 A`
4. **Compute lower-branch current**: For the lower path, R2 and R3 are in series, so their resistances add: 2 plus 4 is 6 ohms. The branch current is 12 over 6, which is 2 A, so A3 reads 2 A.
   - board: `2+4=6Ω; I=2A` · `A3 = 2 A`
5. **Split voltage across R2 and R3**: Now use that same 2 A through each series resistor. V3 is across R2, so 2 A times 2 ohms gives 4 V; V4 is across R3, so 2 A times 4 ohms gives 8 V.
   - board: `V=IR` · `V3 = 4 V` · `V=IR` · `V4 = 8 V`
6. **Total current and final readings**: Finally, A1 is before the split, so it measures the total current: 3 A plus 2 A equals 5 A. Final answer: A1 is 5 A, A2 is 3 A, A3 is 2 A, V3 is 4 V, and V4 is 8 V.
   - board: `A1 = 5 A` · `3 A` · `2 A`
   - sketch: `flowchart TD ; A[12 V source] --> B[Parallel branches] ; B --> C[R1: 4 ohm] ; B --> D[R2+R3: 6 ohm] ; C --> E[3 A] ; D --> F[2 A] ; E --> G[Total 5 A] ; F --> G`

