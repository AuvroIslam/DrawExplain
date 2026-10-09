# Lesson transcripts: L3

Backend 6085db5 (Add results log of all measurements) + uncommitted changes. solver-backed simulation + GPU perception.
Every lesson of the benchmark, as the student hears it (narration) and sees it (board text, sketch), with the automatic checks. Board texts attached to a lettered node show the letter first. Made by backend/scripts/eval_lessons.py.

## dijkstra_AtoE, run 1

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 5/5 (init PASS, relax_A PASS, relax_I_all PASS, order PASS, answer PASS). Lesson 23.611 s, 6 steps, model gpt-5.5.

**Shortest Path from A to E**: We’ll run Dijkstra’s algorithm on this graph starting at A and stop as soon as E is finalized. The shortest path will emerge from the tentative distance updates, not from guessing by eye.

1. **Orient: what we’re solving**: Your question lives right inside this Dijkstra graph: shortest path from A to E. We’ll start at A with distance 0, then let the algorithm prove the cheapest route.
   - board: `a: A = 0`
2. **Iteration 1: finalize A**: Dijkstra picks the unvisited vertex with the smallest tentative distance, so A is finalized first. From A, we write every new neighbor distance: B 5, G 9, H 18, and I 1.
   - board: `a: 0 ✓` · `b: B ∞→5` · `g: G ∞→9` · `h: H ∞→18`
3. **Iteration 1 continued: I gets the best early clue**: The last A-neighbor is I through the edge labeled 1. That tiny cost makes I the next smallest tentative distance, so it will be chosen next.
   - board: `I ∞→1` · `a -> ?: cost 1`
4. **Iteration 2: finalize I and relax outward**: Now I has the smallest tentative distance, 1, so I becomes final. Relaxing I updates C to 7, E to 3, and improves G from 9 down to 4.
   - board: `1 ✓` · `c: C ∞→7` · `e: E ∞→3` · `g: G 9→4`
5. **Iteration 3: E is finalized, so stop**: Among unvisited vertices, E now has the smallest tentative distance, 3. Once E is finalized, Dijkstra says that distance is locked: the shortest route is A to I to E, total 3.
   - board: `e: 3 ✓ final` · `a -> ?: 1` · `? -> e: 2` · `a+e: 1+2=3`
   - sketch: `flowchart LR ; A[A 0] --> I[I 1] ; I --> E[E 3] ; E --> Stop[stop: target] ; A --> Relax[relax neighbors] ; Relax --> I`
6. **Recap: the answer**: So the shortest path from A to E is not through C or G first; Dijkstra locks it in when E becomes final. Answer: A → I → E with total cost 3.

## dijkstra_AtoE, run 2

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 5/5 (init PASS, relax_A PASS, relax_I_all PASS, order PASS, answer PASS). Lesson 24.516 s, 6 steps, model gpt-5.5.

**Shortest Path from A to E**: We run Dijkstra’s algorithm on this graph starting at A and stop as soon as E is finalized. The shortest path is found by repeatedly locking in the smallest tentative distance and relaxing its outgoing edges.

1. **Orient: we are tracing A to E**: Great question: to get the shortest path from A to E, we’ll trace Dijkstra’s Algorithm on this graph, starting at A and stopping when E is finalized.
2. **Iteration 1: finalize A**: Dijkstra starts with A at 0 and everyone else at infinity. The smallest unvisited distance is A, so A becomes locked in; then we relax A’s neighbors.
   - board: `a: A 0 ✓` · `b: B ∞→5` · `g: G ∞→9`
3. **Finish A’s relaxations**: Still from A, the edge to H costs 18 and the edge to I costs 1. These are the first tentative distances for H and I.
   - board: `h: H ∞→18` · `I ∞→1`
4. **Iteration 2: finalize I**: Now the smallest unvisited tentative distance is I with 1, so I is finalized. From I, we update C, E, and improve G because 1 plus 3 beats 9.
   - board: `I 1 ✓` · `c: C ∞→7` · `e: E ∞→3`
5. **I improves G too**: Do not skip the other relaxations: I also reaches G with cost 1 plus 3, so G improves from 9 to 4. That matters because Dijkstra keeps the best known cost so far.
   - board: `g: G 9→4` · `a -> ?: cost 1` · `? -> e: cost 2`
6. **Iteration 3: E is finalized**: Next, the smallest unvisited distance is E with 3, so E is finalized and we stop. The answer is A to I to E, total cost 1 plus 2 equals 3.
   - board: `e: E 3 ✓` · `1+2=3`
   - sketch: `flowchart TD ; A[Start A=0] ; B[Finalize A] ; C[Relax A edges] ; D[Finalize I] ; E[Relax I edges] ; F[Finalize E] ; G[Path A-I-E] ; A --> B ; B --> C ; C --> D ; D --> E ; E --> F ; F --> G`

## dijkstra_AtoE, run 3

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 5/5 (init PASS, relax_A PASS, relax_I_all PASS, order PASS, answer PASS). Lesson 21.318 s, 6 steps, model gpt-5.5.

**Shortest path from A to E**: We’ll run Dijkstra’s algorithm from A and stop as soon as E is finalized. On this graph, the shortest path is A → I → E with total cost 3.

1. **Orient: where the answer lives**: You asked how to get from A to E shortest. This page is Dijkstra’s algorithm: keep the cheapest tentative distance, finalize the smallest, and relax its neighbors.
2. **Initialize and finalize A**: Start with A at 0 and everyone else at infinity. The smallest tentative distance is A, so A becomes final first; now we relax every edge leaving A.
   - board: `a: A 0 ✓` · `b: B ∞→5` · `g: G ∞→9` · `I ∞→1`
3. **Finish A’s relaxations**: One more neighbor of A changes: H gets cost 18. So after A, our frontier is I at 1, B at 5, G at 9, and H at 18.
   - board: `h: H ∞→18`
4. **Finalize I and relax from I**: Now the smallest unvisited value is I at 1, so I is finalized. From I, C becomes 7, E becomes 3, and G improves from 9 down to 4.
   - board: `I 1 ✓` · `c: C ∞→7` · `e: E ∞→3` · `g: G 9→4`
5. **Finalize E: target reached**: Next smallest is E at 3, and since E is the target, Dijkstra stops right here. The predecessor chain is E came from I, and I came from A.
   - board: `e: E 3 ✓` · `a -> ?: cost 1` · `? -> e: cost 2`
6. **Answer: A → I → E**: So the shortest path from A to E is A → I → E, with total cost 1 + 2 = 3. The key is that E became final at 3, so no later route can beat it.
   - board: `e: total = 3`
   - sketch: `flowchart TD ; A[Start A=0] --> B[Finalize A] ; B --> C[Relax A edges] ; C --> D[Finalize I] ; D --> E[Relax I edges] ; E --> F[Finalize E] ; F --> G[Path A-I-E]`

## tcp_cwnd, run 1

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 5/5 (starts_at_1 PASS, doubling PASS, concrete_threshold PASS, additive PASS, timeout PASS). Lesson 21.514 s, 6 steps, model gpt-5.5.

**TCP CongWin Until Timeout**: This page explains how TCP’s congestion window grows in two phases—Slow Start, then Additive Increase—and what a timeout does to reset it. I’ll use an illustrative example with ssthresh = 8 MSS to answer how CongWin changes from the start until timeout.

1. **Orient: three rules control CongWin**: Your question lives in these three rules: start fast, then grow gently, then timeout cuts back. I’ll use an example with ssthresh = 8 MSS so we can watch CongWin move round by round.
2. **Slow Start: double until threshold**: We begin where the slide says CongWin = 1 MSS. In slow start, each ACK adds 1 MSS, so across round trips the window doubles: 1 to 2 to 4 to 8.
   - board: `cwnd 1→2→4→8` · `ssthresh = 8`
3. **Threshold reached: switch phases**: At cwnd = 8, we hit ssthresh, so slow start stops. Now congestion avoidance takes over: instead of doubling, it adds about 1 MSS per RTT.
   - board: `switch here` · `+1 per RTT`
4. **Additive Increase: climb slowly**: Continuing the example, congestion avoidance moves one MSS at a time. The next rounds are cwnd 8, 9, 10, 11, then 12 just before the timeout.
   - board: `8→9→10→11→12` · `round 8`
5. **Timeout: threshold halves, cwnd resets**: Now the timeout rule fires at cwnd = 12. The slide says Threshold = ½ CongWin, so ssthresh becomes 6, and CongWin drops all the way back to 1 MSS.
   - board: `12/2 = 6` · `cwnd 12→1`
6. **Answer: the full change sequence**: So, from the start until timeout, CongWin goes 1, 2, 4, 8, 9, 10, 11, 12, then timeout resets it to 1. After that it slow-starts again toward the new ssthresh = 6.
   - board: `1,2,4,8,9,10,11,12→1` · `hit ssthresh`
   - sketch: `flowchart LR ; A[Start cwnd 1] --> B[Slow start] ; B --> C[Hit ssthresh] ; C --> D[Additive increase] ; D --> E[Timeout] ; E --> F[cwnd 1, halve threshold]`

## tcp_cwnd, run 2

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 5/5 (starts_at_1 PASS, doubling PASS, concrete_threshold PASS, additive PASS, timeout PASS). Lesson 23.987 s, 6 steps, model gpt-5.5.

**TCP Congestion Window: Start to Timeout**: This page explains how TCP grows CongWin first by Slow Start, then Additive Increase, and what happens on a timeout. We’ll run an illustrative example with ssthresh = 8 MSS to answer how the window changes over time.

1. **Where the answer lives**: Your question lives in these three rules: grow fast, grow slowly, then drop on timeout. I’ll use an example threshold of 8 MSS so we can watch CongWin change round by round.
   - board: `example: ssthresh=8`
2. **Slow Start: exponential climb**: In Slow Start, each ACK adds 1 MSS, so over each round trip the window doubles. Starting at 1 MSS, the rounds go 1 to 2 to 4 to 8, stopping when it reaches the threshold.
   - board: `cwnd 1→2→4→8` · `until threshold`
3. **Additive Increase: linear climb**: Now CongWin has reached ssthresh, so TCP switches to congestion avoidance. Here it adds only about 1 MSS per round trip: 8, 9, 10, 11, then 12.
   - board: `cwnd 8→9→10→11→12` · `then AI`
4. **Timeout: multiplicative decrease**: At round 8, suppose the timeout happens when cwnd is 12 MSS. The timeout rule cuts the threshold to half, 12 over 2 equals 6, and resets CongWin to 1 MSS.
   - board: `ssthresh 12/2=6` · `cwnd 12→1`
5. **After timeout, Slow Start restarts**: After the drop, TCP starts Slow Start again, but with the new threshold 6. The next rounds are 1, 2, 4, then capped at 6 before additive increase resumes to 7.
   - board: `restart SS` · `cwnd 1→2→4→6` · `then 6→7`
6. **Plain answer**: So from the start until timeout, the example CongWin sequence is 1, 2, 4, 8, 9, 10, 11, 12, then timeout drops it to 1. That is fast exponential growth, slow linear growth, then multiplicative decrease.
   - board: `1,2,4,8,9,10,11,12→1`
   - sketch: `flowchart LR ; A[Start cwnd 1] ; B[Slow Start] ; C[Reach ssthresh] ; D[Additive Increase] ; E[Timeout] ; F[cwnd 1 again] ; A-->B ; B-->C ; C-->D ; D-->E ; E-->F`

## tcp_cwnd, run 3

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 5/5 (starts_at_1 PASS, doubling PASS, concrete_threshold PASS, additive PASS, timeout PASS). Lesson 21.289 s, 6 steps, model gpt-5.5.

**TCP CongWin: Start to Timeout**: This page shows how TCP’s congestion window grows in two phases—Slow Start then Additive Increase—and what happens at a timeout. I’ll use an illustrative example with ssthresh = 8 MSS to trace cwnd round by round until the timeout reset.

1. **Orient: the three rules**: This page answers your question by chaining three rules: Slow Start grows fast, Additive Increase grows gently, then timeout triggers Multiplicative Decrease. I’ll circle the three rule headings first.
2. **Slow Start begins at 1 MSS**: The slide gives no concrete numbers, so let’s use an example: start cwnd at 1 MSS and set the threshold to 8 MSS. In Slow Start, each ACK adds 1, so per round the window doubles: 1 to 2 to 4 to 8.
   - board: `example: ssthresh=8` · `cwnd 1→2→4→8`
3. **Reaching threshold switches phase**: At cwnd 8, we have reached the threshold, so Slow Start stops. Follow my arrow down: the next ACKs use Congestion Avoidance instead of doubling.
   - board: `after threshold` · `no more doubling`
4. **Additive Increase grows by one per RTT**: Now the rule is gentler: each ACK adds 1/n, which totals about +1 MSS per RTT. So our example continues 8 to 9 to 10 to 11 to 12 before the timeout hits.
   - board: `8→9→10→11→12`
5. **Timeout cuts threshold and resets cwnd**: At round 8, the timeout occurs while cwnd is 12. This rule halves the threshold to 6, and resets CongWin to 1 MSS, so Slow Start begins again.
   - board: `12/2=6; cwnd=1` · `restart`
6. **After timeout: grow again to new threshold**: With the new threshold 6, the restarted Slow Start goes 1 to 2 to 4 to 6, capped at the threshold. So the answer is: cwnd sequence 1, 2, 4, 8, 9, 10, 11, 12, then timeout resets it to 1.
   - board: `new: 1→2→4→6`
   - sketch: `flowchart LR ; A[cwnd=1] ; B[Slow Start] ; C[hit threshold] ; D[Additive Increase] ; E[timeout] ; F[cwnd=1 again] ; A --> B ; B --> C ; C --> D ; D --> E ; E --> F`

## flowchart_invalid_twice, run 1

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 21.604 s, 6 steps, model gpt-5.5.

**Invalid Twice in a Validation Loop**: The flowchart keeps cycling through Read input → Valid? → Show error whenever the answer is No. If the input is invalid twice, the loop shows the error twice and asks for input a third time.

1. **Find the loop we’ll trace**: Great question: if input is invalid twice, we follow the No branch twice. I’ll circle the validation decision because that diamond controls whether we loop or move on.
2. **First invalid input**: Start by reading the first answer, then the diamond checks it. Because it is invalid, my red arrow follows No down to Show error.
   - board: `check input` · `invalid #1` · `error shown 1×`
3. **Loop back for another try**: After showing the error, the line loops back to Read input. That means the program does not end; it asks again.
   - board: `try again` · `attempt #2`
4. **Second invalid input**: Now the second answer is checked the same way. If it is invalid again, we take No again and show the error a second time.
   - board: `check again` · `invalid #2` · `error shown 2×`
5. **What happens next?**: So after two invalid inputs, the program is back at Read input waiting for attempt three. It will only process data when Valid? is Yes.
   - board: `attempt #3` · `only if yes`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`
6. **Plain answer**: Answer: invalid twice means two error messages, then a third input prompt. The loop repeats until one input passes the check.

## flowchart_invalid_twice, run 2

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 17.881 s, 5 steps, model gpt-5.5.

**Invalid Twice in the Validation Loop**: If the input is invalid twice, the flowchart follows the “No” branch twice: each time it shows an error and loops back to read input again. It only processes data after a later input passes the “Valid?” decision.

1. **Find the loop we care about**: Great question—if input is invalid twice, the answer lives in this loop around the Valid? decision. I’m circling the decision, because every attempt must pass through that check.
2. **First invalid input**: First attempt: we read input, ask Valid?, and the answer is No. So the flow goes down to Show error before trying again.
   - board: `attempt 1` · `invalid` · `error #1`
3. **Loop back and try again**: After showing the error, the arrow loops back to Read input. That means the program does not stop; it asks again.
   - board: `ask again`
4. **Second invalid input**: Now the second attempt follows the same rule: Read input, test Valid?, then No again. So we show the error a second time and loop back again.
   - board: `attempt 2` · `invalid again` · `error #2`
5. **When it finally becomes valid**: Only when a later input is valid does the flow take the Yes arrow to Process data, then End. So invalid twice means two errors, two retries, and no processing yet.
   - board: `valid later` · `finish` · `repeat until yes`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`

## flowchart_invalid_twice, run 3

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 17.094 s, 6 steps, model gpt-5.5.

**Invalid Twice in the Validation Loop**: This flowchart keeps sending invalid input through the error branch and back to “Read input.” If the input is invalid twice, the loop repeats twice before it can move on.

1. **Where the answer lives**: Great question: invalid twice means we follow the No loop twice. I’ll circle the decision point, because every repeat is controlled right here.
2. **First invalid attempt**: Attempt 1 starts at Read input, then the check asks Valid? Since it is invalid, follow my red arrow down to Show error.
   - board: `check input` · `invalid #1` · `error shown once`
3. **Loop back and try again**: After the error, the flow does not end. This return arrow takes us back to Read input, so the program asks the user again.
   - board: `ask again` · `attempt 2 begins`
4. **Second invalid attempt**: Now attempt 2 is checked the same way. If it is invalid again, we go down to Show error a second time and loop back again.
   - board: `check again` · `invalid #2` · `error shown twice` · `retry`
5. **When does it stop?**: The loop only exits when Valid? gets a Yes. Then it processes the data and reaches End; two invalid tries do not stop the program.
   - board: `valid input` · `finish`
   - sketch: `flowchart LR ; A[Read input] --> B{Valid?} ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`
6. **Plain answer**: So if the input is invalid twice: Read input, Show error, repeat; Read input, Show error, repeat again. The next stop is another Read input, waiting for a valid try.

## math_calvin_cycle, run 1

Question: "How many ATP and NADPH does this cycle use to fix 3 CO₂, and what happens to the 6 GAP?" (math_calvin_cycle.png)
Score 4/5 (fixation FAIL, reduction_cost PASS, regeneration_cost PASS, totals PASS, gap_split PASS). Lesson 21.267 s, 6 steps, model gpt-5.5.

**Calvin Cycle: Energy Cost and GAP Fate**: This diagram shows the Calvin cycle fixing 3 CO₂ into triose phosphates. For 3 CO₂, it uses 9 ATP and 6 NADPH total; of the 6 GAP made, 1 GAP exits as product while 5 GAP recycle to regenerate RuBP.

1. **Find the carbon input**: Great question—this page tracks what it costs to fix 3 CO₂. I’ll circle the 3 CO₂ input and the cycle product area where the GAP count is split.
2. **Add the ATP costs**: Now watch the red ATP labels: first 6 ATP are spent converting 3-P-glycerate into 1,3-bP-glycerate. Later, 3 more ATP regenerate Ribulose-1,5-bP, so the ATP total is 6 plus 3 equals 9.
   - board: `6+3=9 ATP`
3. **Count the NADPH cost**: The blue reducing power is simpler: the diagram shows 6 NADPH/H⁺ going into the reduction step. They become 6 NADP⁺, so the cycle uses 6 NADPH for these 3 CO₂.
   - board: `electrons used` · `uses 6 NADPH`
4. **Split the 6 GAP**: Here is the key GAP split: 6 GAP are produced after reduction. One GAP exits to the right as net sugar product, while 5 GAP turn downward into regeneration.
   - board: `1 exits` · `5 recycle`
5. **Regenerate the CO₂ acceptor**: Those 5 recycled GAP rearrange into 3 Ribulose-5-P, then the 3 ATP step phosphorylates them back to 3 Ribulose-1,5-bP. That regenerated RuBP is ready to accept the next 3 CO₂.
   - board: `rearrange` · `phosphorylate` · `CO₂ acceptor reset`
6. **Answer in one line**: So for 3 CO₂, the cycle spends 9 ATP and 6 NADPH. The 6 GAP become 1 exported GAP plus 5 recycled GAP that rebuild RuBP.
   - sketch: `flowchart LR ; A[3 CO2 enter] --> B[Use 9 ATP] ; B --> C[Use 6 NADPH] ; C --> D[Make 6 GAP] ; D --> E[1 GAP exits] ; D --> F[5 GAP recycle] ; F --> G[RuBP rebuilt]`

Missing: fixation: MISSING any: 0 of 3 matched, need 1

## math_calvin_cycle, run 2

Question: "How many ATP and NADPH does this cycle use to fix 3 CO₂, and what happens to the 6 GAP?" (math_calvin_cycle.png)
Score 5/5 (fixation PASS, reduction_cost PASS, regeneration_cost PASS, totals PASS, gap_split PASS). Lesson 17.269 s, 6 steps, model gpt-5.5.

**Calvin Cycle Inputs and GAP Fate**: This diagram tracks the Calvin cycle for fixing 3 CO₂. The key answer is that 9 ATP and 6 NADPH are used, producing 6 GAP total: 1 GAP leaves as product and 5 GAP are recycled to regenerate RuBP.

1. **Find the 3 CO₂ starting point**: We’re answering: for these 3 CO₂, what energy goes in, and where do the 6 GAP go? I’ll circle the CO₂ entry first, because all the numbers on this page are scaled to that.
   - board: `carbon input`
2. **ATP used in the reduction phase**: First ATP cost: the 6 molecules of 3-P-glycerate are phosphorylated to 1,3-bP-glycerate. The red ATP arrow tells us this step spends 6 ATP and makes 6 ADP.
   - board: `adds phosphate` · `6 ATP spent`
3. **NADPH used to make GAP**: Next, NADPH reduces 1,3-bP-glycerate into GAP. Follow my blue arrow: 6 NADPH are oxidized to 6 NADP⁺, and phosphate is released.
   - board: `reduction` · `electrons donated`
4. **One GAP exits, five recycle**: Here is the split that answers the GAP question. The diagram shows 6 GAP made: 1 GAP exits on the right, while 5 GAP continue downward to rebuild the 3 five-carbon acceptors.
   - board: `1 exits` · `5 recycle`
5. **Extra ATP regenerates RuBP**: Those 5 GAP are rearranged into 3 ribulose-5-P, then ATP finishes the reset to ribulose-1,5-bP. That adds 3 more ATP, so total ATP is 6 plus 3 equals 9.
   - board: `rearrange carbons` · `6+3=9 ATP`
6. **Final accounting**: So the answer is: fixing 3 CO₂ uses 9 ATP and 6 NADPH. Of the 6 GAP, 1 leaves as sugar-building product and 5 are recycled to regenerate RuBP.
   - sketch: `flowchart LR ; A[3 CO2 enter] --> B[6 PGA form] ; B --> C[Use 6 ATP] ; C --> D[Use 6 NADPH] ; D --> E[6 GAP] ; E --> F[1 GAP exits] ; E --> G[5 GAP recycle] ; G --> H[Use 3 ATP]`

## cs_bst_insert, run 1

Question: "How would you insert 5 into this binary search tree? Show the comparisons, where 5 ends up, and the in-order traversal afterwards." (cs_bst_insert.png)
Score 5/5 (left_at_8 PASS, right_at_3_left_at_6 PASS, right_child_of_4 PASS, search_path PASS, inorder_after PASS). Lesson 31.565 s, 5 steps, model gpt-5.5.

**Insert 5 into the BST**: We’ll insert 5 by following the binary search tree rule: smaller values go left, larger values go right. Then we’ll read the tree in-order to see the sorted sequence.

1. **Start at the root**: We’re inserting 5 into this binary search tree. Start at the root 8: since 5 is less than 8, follow my arrow to the left child.
   - board: `5 < 8` · `go left`
2. **Compare with 3**: Now compare 5 with the node 3. Because 5 is greater than 3, we turn right from 3 toward 6.
   - board: `5 > 3` · `go right`
3. **Compare with 6**: At 6, compare again: 5 is less than 6. So we go left, landing on the child 4.
   - board: `5 < 6` · `go left`
4. **Find the empty spot**: Now compare 5 with 4. Since 5 is greater than 4, it should go to 4’s right, and that spot is empty—so 5 becomes the right child of 4.
   - board: `5 > 4` · `insert 5 here`
5. **In-order traversal after insertion**: In-order means left, node, right. After inserting 5, the sorted walk is 1, 3, 4, 5, 6, 7, 8, 10, 13, 14.
   - board: `5 inserted` · `1,3,4,5,6,7,8,10,13,14`
   - sketch: `flowchart TD ; A[Start at 8] --> B[5 < 8] ; B --> C[Go to 3] ; C --> D[5 > 3] ; D --> E[Go to 6] ; E --> F[5 < 6] ; F --> G[Insert after 4]`

## cs_bst_insert, run 2

Question: "How would you insert 5 into this binary search tree? Show the comparisons, where 5 ends up, and the in-order traversal afterwards." (cs_bst_insert.png)
Score 5/5 (left_at_8 PASS, right_at_3_left_at_6 PASS, right_child_of_4 PASS, search_path PASS, inorder_after PASS). Lesson 21.953 s, 6 steps, model gpt-5.5.

**Inserting 5 into the BST**: We’ll follow the binary search tree rule: smaller values go left, larger values go right. For 5, the comparisons lead us to place it as the left child of 6, then the in-order traversal becomes sorted.

1. **Start at the root**: We insert 5 by starting at the root, the 8 I just circled. In a BST, each comparison decides left for smaller or right for larger.
   - board: `start here`
2. **Compare 5 with 8**: First comparison: 5 is less than 8, so we follow the left arrow from 8 down to 3. That keeps us in the smaller-than-8 side of the tree.
   - board: `5 < 8` · `go left`
3. **Compare 5 with 3**: Now compare at 3: 5 is greater than 3, so we turn right to 6. Notice how the path is narrowing the only legal place for 5.
   - board: `5 > 3` · `go right`
4. **Compare 5 with 6**: At 6, 5 is less than 6, so we go left. The left child there is 4, so we need one more comparison instead of inserting yet.
   - board: `5 < 6` · `go left`
5. **Compare 5 with 4, then insert**: At 4, 5 is greater than 4, so it belongs on 4’s right side. That spot is empty, so we draw the new 5 right there.
   - board: `5 > 4` · `insert`
6. **In-order traversal after insertion**: Now do in-order traversal: left subtree, node, right subtree. After inserting 5, the sorted order is 1, 3, 4, 5, 6, 7, 8, 10, 13, 14.
   - board: `new node` · `1,3,4,5,6,7,8,10,13,14`
   - sketch: `flowchart TD ; A[Compare at node] --> B{5 smaller?} ; B -->\|yes\| C[go left] ; B -->\|no\| D[go right] ; C --> E[empty spot?] ; D --> E ; E -->\|yes\| F[insert 5] ; E -->\|no\| A`

## cs_bfs_dfs, run 1

Question: "In which order does breadth-first search visit the nodes if it starts at A and takes neighbours in alphabetical order? How would depth-first search from A differ?" (cs_bfs_dfs.png)
Score 5/5 (bfs_order PASS, bfs_queue PASS, bfs_levels PASS, dfs_order PASS, dfs_mechanism PASS). Lesson 33.433 s, 6 steps, model gpt-5.5.

**BFS vs DFS from A**: We’ll run breadth-first search on this graph starting at A, using alphabetical neighbour order. Then we’ll contrast it with depth-first search, which dives down one branch before coming back.

1. **Orient: start at A**: We’re answering the visit order question, starting at A. For BFS, the key tool is a FIFO queue, so A is seen first and waits to be processed.
   - board: `a: Q=[A], seen`
2. **BFS step 1: visit A**: Now dequeue A and visit it. Alphabetically, its neighbours are B, C, then E, so those three are marked seen and placed in the queue.
   - board: `a: ✓ visit 1` · `b: seen, p=A` · `c: seen, p=A` · `e: seen, p=A`
3. **BFS step 2: visit B**: Next the FIFO queue gives B, not C’s child yet. Visiting B discovers D and F in alphabetical order, so the queue becomes C, E, D, F.
   - board: `b: ✓ visit 2` · `d: seen, p=B` · `f: seen, p=B` · `Q=[C,E,D,F]`
4. **BFS steps 3 and 4: visit C, then E**: The queue front is C, so C is visited before E. C adds G; then E is visited and adds nothing new, because its neighbours are already seen.
   - board: `c: ✓ visit 3` · `g: seen, p=C` · `e: ✓ visit 4` · `Q=[D,F,G]`
5. **BFS steps 5–7: finish the queue**: Now BFS simply drains the remaining queue: D, then F, then G. That gives the final BFS order A, B, C, E, D, F, G.
   - board: `d: ✓ visit 5` · `f: ✓ visit 6` · `g: ✓ visit 7` · `BFS: A,B,C,E,D,F,G`
6. **How DFS differs**: DFS uses a stack-like idea: take the alphabetically first unvisited neighbour and keep diving. From A that path goes A, B, D, then backtracks to F, E, C, G, so DFS differs by going deep before wide.
   - board: `a -> b: DFS dives` · `b -> d: first child` · `DFS: A,B,D,F,E,C,G`
   - sketch: `flowchart LR ; A[Start A] --> B[BFS queue] ; B --> C[Visit level order] ; A --> D[DFS stack] ; D --> E[Dive first] ; C --> F[Wide before deep] ; E --> G[Deep before wide]`

## cs_bfs_dfs, run 2

Question: "In which order does breadth-first search visit the nodes if it starts at A and takes neighbours in alphabetical order? How would depth-first search from A differ?" (cs_bfs_dfs.png)
Score 5/5 (bfs_order PASS, bfs_queue PASS, bfs_levels PASS, dfs_order PASS, dfs_mechanism PASS). Lesson 26.606 s, 7 steps, model gpt-5.5.

**BFS vs DFS from A**: We run breadth-first search on the shown graph starting at A, using a FIFO queue and alphabetical neighbour order. Then we compare how depth-first search would differ: it follows one branch deeply before backing up.

1. **Orient: BFS starts at A**: We’re answering the visit order from A. I’ll circle A as the start, and BFS will use a queue, so it visits all level-1 neighbours before going deeper.
   - board: `a: start; Q=[A]`
2. **BFS step 1: visit A**: First we dequeue A and visit it. In alphabetical order, A’s neighbours are B, C, and E, so they enter the back of the queue as level 1.
   - board: `a: ✓ visit 1` · `b: seen L1` · `c: seen L1` · `e: seen L1`
3. **BFS step 2: visit B**: Next the FIFO queue gives us B, not C by choice but because B was enqueued first. B adds its unvisited alphabetical neighbours D and F, so the queue becomes C, E, D, F.
   - board: `b: ✓ visit 2` · `d: seen L2` · `f: seen L2` · `Q=[C,E,D,F]`
4. **BFS step 3: visit C**: Now C comes off the front. Its only unvisited neighbour here is G, so G is marked and placed after F in the queue.
   - board: `c: ✓ visit 3` · `g: seen L2` · `Q=[E,D,F,G]`
5. **BFS steps 4–5: visit E, then D**: The queue front is E, so E is visit 4; it adds nothing new. Then D is visit 5, and it also adds nothing new because its neighbour B is already seen.
   - board: `e: ✓ visit 4` · `Q=[D,F,G]` · `d: ✓ visit 5` · `Q=[F,G]`
6. **BFS steps 6–7: finish F, G**: Finally F is visit 6, then G is visit 7. The queue is empty, so BFS is done: A, B, C, E, D, F, G.
   - board: `f: ✓ visit 6` · `g: ✓ visit 7` · `a+b+c+e+d+f+g: A,B,C,E,D,F,G`
   - sketch: `flowchart TD ; A[Start A] --> B[Dequeue front] ; B --> C[Visit node] ; C --> D[Enqueue unseen] ; D --> E{Queue empty?} ; E -->\|no\| B ; E -->\|yes\| F[Done]`
7. **How DFS would differ**: DFS uses a stack or recursion, so it dives down the alphabetically first branch before returning. From A that gives A, B, D, F, E, C, G instead of BFS’s level-by-level order.
   - board: `a -> b: DFS dives` · `b -> d: first branch` · `a+b+c+e+d+f+g: DFS: A,B,D,F,E,C,G`

## cs_dijkstra_a_to_e, run 1

Question: "Use Dijkstra's algorithm starting at A: what are the shortest distances to the other nodes, and what is the shortest path from A to E?" (cs_dijkstra_a_to_e.png)
Score 5/5 (b_stays_4 PASS, d_is_5 PASS, e_is_10 PASS, path_a_c_e PASS, via_d_is_12 PASS). Lesson 25.111 s, 6 steps, model gpt-5.5.

**Dijkstra from A to E**: We run Dijkstra’s algorithm on the weighted graph starting at A. The shortest distances settle as A=0, C=2, B=4, D=5, E=10, giving the path A → C → E.

1. **Set up the start state**: We’ll answer by running Dijkstra from A: start A at 0, and every other node at infinity. I’m circling the source, because every tentative distance will grow outward from here.
   - board: `a: A = 0` · `b: ∞` · `c: ∞`
2. **Iteration 1: finalize A**: Smallest unvisited distance is A at 0, so A is finalized. Relax A’s two edges: B becomes 4 through weight 4, and C becomes 2 through weight 2.
   - board: `a: ✓ done` · `b: B ∞→4` · `c: C ∞→2`
3. **Iteration 2: finalize C**: Now C has the smallest tentative distance, 2, so C is finalized. From C: B would be 7 so it stays 4, D improves to 5, and E improves to 10.
   - board: `c: ✓ done` · `b: stays 4` · `d: D ∞→5` · `e: E ∞→10`
4. **Iterations 3 and 4: finalize B, then D**: Next smallest is B at 4, so finalize B; its route to D would be 14, not better than 5. Then D at 5 finalizes, and D to E would be 12, not better than 10.
   - board: `b: ✓ done` · `d: ✓ done` · `e: stays 10`
5. **Iteration 5: finalize E and read the path**: Finally E is the smallest unvisited node at 10, so Dijkstra stops for our target. Trace predecessors backward: E came from C, and C came from A, so the path is A to C to E.
   - board: `e: E=10 ✓` · `a -> c: cost 2` · `c -> e: cost 8`
6. **Final answer**: So the shortest distances from A are A 0, B 4, C 2, D 5, and E 10. The shortest path to E is A → C → E, with total cost 2 + 8 = 10.
   - sketch: `flowchart LR ; A[A 0] --> C[C 2] ; C --> B[B 4] ; C --> D[D 5] ; C --> E[E 10] ; D --> E`

## cs_dijkstra_a_to_e, run 2

Question: "Use Dijkstra's algorithm starting at A: what are the shortest distances to the other nodes, and what is the shortest path from A to E?" (cs_dijkstra_a_to_e.png)
Score 5/5 (b_stays_4 PASS, d_is_5 PASS, e_is_10 PASS, path_a_c_e PASS, via_d_is_12 PASS). Lesson 21.463 s, 6 steps, model gpt-5.5.

**Dijkstra from A to E**: We run Dijkstra’s algorithm on the weighted graph starting at A. The shortest distances settle in order A, C, B, D, E, and the shortest path to E is A → C → E with total cost 10.

1. **Set up the start**: We’ll answer this by running Dijkstra from A: start A at 0, and every other node at infinity. I’m circling A because it is the source, the only distance we know for sure at the beginning.
   - board: `a: A = 0` · `b: B = ∞` · `c: C = ∞`
2. **Iteration 1: finalize A**: Smallest tentative distance is A with 0, so A becomes final. Now relax A’s edges: A to B gives 0+4, and A to C gives 0+2.
   - board: `a: ✓ final` · `b: B ∞→4` · `c: C ∞→2`
3. **Iteration 2: finalize C**: Next smallest is C with 2, so C is final. Relax from C: B would be 7 so it stays 4; D becomes 5, and E becomes 10.
   - board: `c: ✓ final` · `b: B stays 4` · `d: D ∞→5` · `e: E ∞→10`
4. **Iterations 3 and 4: B then D**: Now B is the smallest unvisited distance, 4, so finalize it; B to D would be 14, not better. Then D at 5 is next; D to E would be 12, still not better than 10.
   - board: `b: ✓ final` · `d: D stays 5` · `d: ✓ final` · `e: E stays 10`
5. **Iteration 5 and final answer**: Finally E is the smallest unvisited node with distance 10, so it is final and we stop. Tracing predecessors gives A to C to E, with total cost 2+8=10.
   - board: `e: ✓ final 10` · `a -> c: cost 2` · `c -> e: cost 8` · `a+c+e: total = 10`
   - sketch: `flowchart LR ; A[Start A=0] --> Pick[Pick smallest] ; Pick --> Final[Finalize node] ; Final --> Relax[Relax edges] ; Relax --> Target{E final?} ; Target -->\|no\| Pick ; Target -->\|yes\| Done[Stop: dist 10]`
6. **Recap: all shortest distances**: So the final shortest distances from A are A=0, C=2, B=4, D=5, and E=10. The requested shortest path to E is A → C → E, not through D, because 12 is larger than 10.

## cs_prim_mst, run 1

Question: "Using Prim's algorithm starting from A, which edges are added to the minimum spanning tree, in what order, and what is the total weight?" (cs_prim_mst.png)
Score 4/5 (edges_ad_df_ab PASS, edges_be_ce_eg PASS, prim_order PASS, total_39 PASS, skips_cycle_edges FAIL). Lesson 32.182 s, 7 steps, model gpt-5.5.

**Prim’s Algorithm from A**: We run Prim’s algorithm on the given weighted graph, starting at A. At each step we add the cheapest edge that connects the growing tree to a new vertex, ending with total MST weight 39.

1. **Start at A**: We’re finding the minimum spanning tree by growing one tree from A. I’ll circle A as the start, then write the first cheapest connections it offers: B costs 7 and D costs 5.
   - board: `b: B ∞→7 via A` · `d: D ∞→5 via A`
2. **Add A-D, then update from D**: Prim picks the cheapest outside connection, so A-D with weight 5 joins the tree. From the D I just added, E becomes reachable at 15 and F at 6.
   - board: `d: ✓ added` · `e: E ∞→15 via D` · `f: F ∞→6 via D`
3. **Add D-F, then improve E and G**: Now the cheapest open connection is D-F with weight 6, so F joins next. F gives E a better route, 15 to 8, and introduces G at 11.
   - board: `f: ✓ added` · `e: E 15→8 via F` · `g: G ∞→11 via F`
4. **Add A-B, then improve C and E**: Among the outside vertices, B has the cheapest connection: A-B with weight 7. Adding B discovers C at 8 and improves E again, from 8 down to 7.
   - board: `b: ✓ added` · `c: C ∞→8 via B` · `e: E 8→7 via B`
5. **Add B-E, then improve C and G**: Next lowest is E through B, so B-E with weight 7 is added. From E, C improves from 8 to 5, and G improves from 11 to 9.
   - board: `e: ✓ added` · `c: C 8→5 via E` · `g: G 11→9 via E`
6. **Add E-C**: Now C has the cheapest outside connection, E-C with weight 5. C joins the tree, and there are no cheaper updates from C.
   - board: `c: ✓ added`
7. **Add E-G and total the tree**: The last outside vertex is G, reached cheapest by E-G with weight 9. So the MST edges are A-D, D-F, A-B, B-E, E-C, E-G, and the total is 39.
   - board: `g: ✓ added` · `5+6+7+7+5+9=39`
   - sketch: `flowchart LR ; A[Start A] --> D[Add A-D] ; D --> F[Add D-F] ; F --> B[Add A-B] ; B --> E[Add B-E] ; E --> C[Add E-C] ; C --> G[Add E-G]`

Missing: skips_cycle_edges: MISSING any: 0 of 4 matched, need 1

## cs_prim_mst, run 2

Question: "Using Prim's algorithm starting from A, which edges are added to the minimum spanning tree, in what order, and what is the total weight?" (cs_prim_mst.png)
Score 4/5 (edges_ad_df_ab PASS, edges_be_ce_eg PASS, prim_order PASS, total_39 PASS, skips_cycle_edges FAIL). Lesson 23.376 s, 7 steps, model gpt-5.5.

**Prim from A: MST Order**: We run Prim’s algorithm directly on this weighted graph, starting at A. Each step adds the cheapest edge from the growing tree to a new vertex, giving total MST weight 39.

1. **Start at A**: We’re answering: which edges does Prim add starting from A? I’ll circle A as the seed tree, then write the first cheapest known connections to its neighbors.
   - board: `B ∞→7` · `d: D ∞→5`
2. **Add A-D, then update from D**: Now the cheapest connection is A-D with weight 5, so D joins the tree. From D, we discover E at 15 and F at 6.
   - board: `d: ✓` · `e: E ∞→15` · `F ∞→6`
3. **Add D-F, then improve E and G**: Among outside vertices, F has the cheapest known connection, so add D-F with weight 6. From F, E improves from 15 to 8, and G becomes 11.
   - board: `✓` · `e: E 15→8` · `g: G ∞→11`
4. **Add A-B, then update C and E**: Next cheapest is B through A, so add A-B with weight 7. B gives C its first connection, and improves E from 8 to 7.
   - board: `✓` · `c: C ∞→8` · `e: E 8→7`
5. **Add B-E, then improve C and G**: Now E is tied at 7 through B, and it is the cheapest outside vertex, so add B-E. From E, C improves to 5 and G improves to 9.
   - board: `e: ✓` · `c: C 8→5` · `g: G 11→9`
6. **Add E-C**: The cheapest outside vertex is C through E, weight 5, so add E-C. There are no cheaper updates from C, so we only mark C finished.
   - board: `c: ✓`
7. **Add E-G and total the tree**: Last outside vertex is G, reached cheapest through E with weight 9. So the MST edges are A-D, D-F, A-B, B-E, E-C, E-G, and the total is 39.
   - board: `g: ✓` · `5+6+7+7+5+9=39`
   - sketch: `flowchart LR ; A[Start A] --> D[Add D] ; D --> F[Add F] ; F --> B[Add B] ; B --> E[Add E] ; E --> C[Add C] ; C --> G[Add G]`

Missing: skips_cycle_edges: MISSING any: 0 of 4 matched, need 1

## math_derivative_tangent, run 1

Question: "The curve is f(x) = x² and the tangent touches it at a = 1. How do I find the tangent line y = mx + b?" (math_derivative_tangent.png)
Score 5/5 (point PASS, derivative PASS, slope PASS, intercept PASS, equation PASS). Lesson 19.706 s, 5 steps, model gpt-5.5.

**Finding the Tangent to x² at 1**: We use the tangent point and derivative slope: for f(x)=x² at a=1, the point is (1,1) and the slope is f′(1)=2. Then we solve y=mx+b to get the tangent line y=2x−1.

1. **Where the tangent information lives**: Great question—this picture is about a curve y=f(x) and its tangent line at the point (a,f(a)). I’ll circle the touch point first, because that one point gives us both x=1 and y=1 here.
2. **Compute the point on f(x)=x²**: Since the question says a=1, plug 1 into f(x)=x². That gives f(1)=1²=1, so the tangent touches the curve at (1,1).
   - board: `a=1` · `f(1)=1` · `point=(1,1)`
3. **Use the derivative for the slope**: Now follow the formula on the page: the tangent has y=mx+b, where m=f′(a). For f(x)=x², the derivative is f′(x)=2x, so m=f′(1)=2.
   - board: `m=2`
4. **Solve for b using the point**: We know the line has slope 2 and passes through (1,1). Substitute into y=mx+b: 1=2(1)+b, so b=-1.
   - board: `plug in` · `1=2(1)+b`
5. **Final tangent line**: So the tangent line is y=2x−1. Big idea: the derivative gives the slope, and the touch point lets us find the intercept.
   - board: `y=2x−1`
   - sketch: `flowchart LR ; A[Choose a=1] --> B[Find point] ; B --> C[Compute derivative] ; C --> D[Get slope] ; D --> E[Solve for b] ; E --> F[Line y=2x-1]`

## math_derivative_tangent, run 2

Question: "The curve is f(x) = x² and the tangent touches it at a = 1. How do I find the tangent line y = mx + b?" (math_derivative_tangent.png)
Score 5/5 (point PASS, derivative PASS, slope PASS, intercept PASS, equation PASS). Lesson 16.947 s, 5 steps, model gpt-5.5.

**Tangent Line at x = 1**: We’ll use the derivative of f(x)=x² to get the tangent slope at a=1, then plug the touch point into y=mx+b to find b.

1. **Where the tangent line comes from**: We’re finding the purple tangent line to y=f(x)=x² at a=1. The key is this touch point: it gives both the slope location and one point on the line.
2. **Find the point on the curve**: Since a=1, the tangent touches the curve at x=1. For f(x)=x², f(1)=1²=1, so the point is (1,1).
   - board: `x=1, y=1` · `(1,1)`
3. **Use derivative for the slope**: Now use the formula on the page: m=f′(a). For f(x)=x², f′(x)=2x, so at a=1 the slope is m=2.
   - board: `slope m=2`
4. **Solve for b**: Put m=2 into y=mx+b, then use the point (1,1). That gives 1=2·1+b, so b=-1.
   - board: `plug in` · `1=2(1)+b` · `b=-1`
5. **Final tangent line**: So the tangent line is y=2x−1. It matches the picture: the purple line crosses the y-axis below zero and just kisses the parabola at (1,1).
   - board: `y=2x−1` · `tangent at 1`
   - sketch: `flowchart LR ; A[a=1] --> B[f(1)=1] ; B --> C[point (1,1)] ; A --> D[f'(1)=2] ; C --> E[1=2+b] ; D --> E ; E --> F[y=2x-1]`

## math_pythagoras, run 1

Question: "How does this picture prove the Pythagorean theorem?" (math_pythagoras_squares.jpg)
Score 4/5 (areas PASS, sides_3_4_5 PASS, sum_9_16_25 PASS, theorem PASS, rearrangement FAIL). Lesson 21.225 s, 6 steps, model gpt-5.5.

**Pythagoras by Area Shuffling**: This picture proves the Pythagorean theorem by placing three squares on the sides of a right triangle, then using the two acute angles to show the big tilted square has the right orientation. The area of the tilted square on the hypotenuse equals the combined areas of the two leg-squares.

1. **Find the theorem in the picture**: Great question: this picture is an area proof of Pythagoras. The green triangle is the right triangle, and the three colored grids are squares built on its three sides.
2. **The side labels set the angles**: Now watch the angles: α and β are the two sharp angles of the right triangle. Because a right triangle has 180 degrees total, α plus β must make 90 degrees.
   - board: `α+β=90°`
3. **Why the tilted shape is a square**: Here is the key geometry move: at the hypotenuse square’s corner, the neighboring triangle angles are α and β. Since α plus β is 90 degrees, the remaining corner is also a right angle, so the tilted red shape is truly a square.
   - board: `angle matches` · `all corners 90°`
4. **Read the side areas from the grids**: The left square is 4 by 4, so its area is 16. The bottom square is 3 by 3, so its area is 9.
   - board: `4² = 16` · `3² = 9`
5. **See the hypotenuse area**: Follow the tilted square: it is a 5 by 5 grid, so its area is 25. That matches 16 plus 9, exactly the Pythagorean relationship.
   - board: `5² = 25` · `16 + 9 = 25`
6. **The proof idea**: So the picture proves Pythagoras by areas: the two leg-squares together equal the hypotenuse-square. In symbols, a² plus b² equals c².
   - board: `part of total` · `part of total` · `a²+b²=c²`
   - sketch: `flowchart LR ; A[Right triangle] --> B[Build 3 squares] ; B --> C[Use α+β] ; C --> D[Hypotenuse square] ; D --> E[Compare areas] ; E --> F[a²+b²=c²]`

Missing: rearrangement: MISSING any: 0 of 4 matched, need 1

## math_pythagoras, run 2

Question: "How does this picture prove the Pythagorean theorem?" (math_pythagoras_squares.jpg)
Score 2/5 (areas FAIL, sides_3_4_5 FAIL, sum_9_16_25 FAIL, theorem PASS, rearrangement PASS). Lesson 21.11 s, 6 steps, model gpt-5.5.

**Pythagoras by Rearranging Squares**: This picture proves the Pythagorean theorem by fitting three squares around a right triangle, then showing the two yellow “leg squares” exactly fill the missing parts of the big tilted square. The area relationship becomes a² + b² = c².

1. **Find the right triangle**: This picture proves Pythagoras by focusing on the pale green right triangle in the middle. I’ll circle the triangle first: its two legs are the sides touching the red and yellow squares, and the slanted side is the hypotenuse.
   - board: `right triangle`
2. **Each side gets a square**: Now look at the three squares built on the triangle’s sides. Red is the square on one leg, yellow below is the square on the other leg, and the tilted red-yellow square is on the hypotenuse.
3. **The tilted square is the hypotenuse square**: The proof’s target is the big tilted square: that whole square sits on the triangle’s slanted side. So its total area represents hypotenuse squared, which we call c².
   - board: `build square` · `area = c²`
4. **The small squares are the leg areas**: The two leg-squares are the ones straight out from the triangle’s legs. Their areas are a² and b², and the grid shows we can compare area by counting matching little squares.
   - board: `area a²`
5. **The key rearrangement**: Here is the clever part: the tilted hypotenuse square is filled by a red block plus yellow border pieces. Those yellow pieces are exactly the same total area as the bottom yellow square, just rearranged.
   - board: `same area`
6. **So a² plus b² equals c²**: So the big tilted square’s area is exactly the left red square plus the bottom yellow square. That is the Pythagorean theorem: a² + b² = c².
   - board: `a² + b² = c²`
   - sketch: `flowchart LR ; A[Right triangle] --> B[Build 3 squares] ; B --> C[Rearrange pieces] ; C --> D[Leg areas fill] ; D --> E[Hypotenuse square] ; E --> F[a²+b²=c²]`

Missing: areas: MISSING all[1] \| MISSING all[2] \| MISSING all[3]; sides_3_4_5: MISSING any: 0 of 6 matched, need 1; sum_9_16_25: MISSING any: 0 of 5 matched, need 1

## math_quadratic, run 1

Question: "Where does this parabola cross the x-axis? Solve its equation step by step." (math_quadratic_roots.png)
Score 5/5 (set_zero PASS, method PASS, root_2 PASS, root_minus_1 PASS, graph_link PASS). Lesson 17.882 s, 5 steps, model gpt-5.5.

**Finding the x-intercepts**: We’ll find where the parabola crosses the x-axis by setting y = 0 and solving the quadratic. The graph confirms the two solutions: x = -1 and x = 2.

1. **The question lives on the x-axis**: We’re looking for where this red parabola crosses the x-axis, so I’ll circle the two crossing spots. At those points, the height is zero: y = 0.
   - board: `y = 0 here`
2. **Set the formula equal to zero**: Now we use the printed equation, y = x² - x - 2. Since x-axis crossings have y = 0, replace y with 0.
   - board: `0 = x²-x-2`
3. **Factor the quadratic**: To solve 0 = x² - x - 2, find two numbers that multiply to -2 and add to -1. Those are -2 and +1, so the factors are x - 2 and x + 1.
   - board: `(x-2)(x+1)=0`
4. **Use the zero-product rule**: If two factors multiply to zero, at least one factor must be zero. So set each factor equal to zero and solve: x - 2 = 0 gives x = 2, and x + 1 = 0 gives x = -1.
   - board: `x = 2` · `x = -1` · `solutions`
5. **Answer: two x-intercepts**: So the parabola crosses the x-axis at x = -1 and x = 2. As coordinate points, the intercepts are (-1, 0) and (2, 0).
   - board: `(-1,0), (2,0)`
   - sketch: `flowchart LR ; A[Set y=0] --> B[Factor quadratic] ; B --> C[Set factors zero] ; C --> D[Get x values] ; D --> E[Plot intercepts]`

## math_quadratic, run 2

Question: "Where does this parabola cross the x-axis? Solve its equation step by step." (math_quadratic_roots.png)
Score 5/5 (set_zero PASS, method PASS, root_2 PASS, root_minus_1 PASS, graph_link PASS). Lesson 16.263 s, 5 steps, model gpt-5.5.

**Finding the x-intercepts**: We solve where the graphed parabola crosses the x-axis by setting y = 0 and factoring the quadratic. The crossings are x = -1 and x = 2, matching the red curve on the graph.

1. **Set up the question**: We’re finding where the red parabola crosses the x-axis. I’ll circle the equation first, because the x-axis crossings happen when y becomes zero.
2. **Make y equal zero**: At any x-intercept, the height is y = 0. So I replace the left side of the equation with zero: 0 = x² - x - 2.
   - board: `y = 0 here` · `0 = x²-x-2`
3. **Factor the quadratic**: Now factor x² - x - 2. We need two numbers that multiply to -2 and add to -1: that’s -2 and +1, so the factors are (x - 2)(x + 1).
   - board: `-2·1=-2, sum=-1` · `0=(x-2)(x+1)`
4. **Use the zero product rule**: If a product equals zero, one factor must be zero. So x - 2 = 0 gives x = 2, and x + 1 = 0 gives x = -1.
   - board: `x = 2` · `x = -1` · `zero factor`
5. **Match the graph**: The graph confirms the algebra: the red curve crosses the x-axis at -1 and 2. So the solutions are x = -1 and x = 2.
   - board: `solutions: -1, 2`
   - sketch: `flowchart LR ; A[Set y=0] --> B[Factor quadratic] ; B --> C[Set factors zero] ; C --> D[Solve x values] ; D --> E[Check crossings]`

## math_unit_circle, run 1

Question: "What is sin(150°) and why?" (math_unit_circle.png)
Score 4/5 (value_half PASS, y_coordinate PASS, point_150 FAIL, reference_30 PASS, quadrant_sign PASS). Lesson 16.06 s, 5 steps, model gpt-5.5.

**Why sin(150°) = 1/2**: On the unit circle, sine is the y-coordinate. The angle 150° sits in Quadrant II with reference angle 30°, so it has the same positive y-value as 30°: 1/2.

1. **Find the angle**: We’re answering: what is sin(150°)? I’ll circle 150° on the unit circle, because sine comes from the point where that angle hits the circle.
   - board: `angle asked`
2. **Sine means y-coordinate**: On this chart, each point is labeled as an ordered pair. Sine is the second number—the y-coordinate—so we need the height of the 150° point.
   - board: `sin = y`
3. **Use the reference angle**: The 150° ray is 30° away from the negative x-axis. That makes its reference angle 30°, so its height matches the 30° point’s height.
   - board: `same height` · `ref angle 30°`
4. **Read the y-value**: At 30°, the labeled point is (√3/2, 1/2), so the y-coordinate is 1/2. At 150°, we keep that same positive height, because we are above the x-axis.
   - board: `y = 1/2`
5. **Final answer**: So sin(150°) = 1/2. Big idea: sine asks for height on the unit circle, and 150° has the same height as 30° but lies in Quadrant II, where sine is positive.

Missing: point_150: MISSING any: 0 of 3 matched, need 1

## math_unit_circle, run 2

Question: "What is sin(150°) and why?" (math_unit_circle.png)
Score 4/5 (value_half PASS, y_coordinate PASS, point_150 FAIL, reference_30 PASS, quadrant_sign PASS). Lesson 18.758 s, 6 steps, model gpt-5.5.

**Why sin(150°) = 1/2**: On the unit circle, sine is the y-coordinate of the point at an angle. Since 150° has a 30° reference angle in Quadrant II, its y-coordinate is positive 1/2.

1. **Find where 150° lives**: We’re answering: what is sin(150°)? I’ll circle 150° on the unit circle, because sine is read from the height of that point.
   - board: `height = sine`
2. **Use the matching point**: Follow the ray out to the blue dot at 150°. The nearby coordinate is negative x, positive y, so sine will be the positive second number.
   - board: `ray lands` · `y-value`
3. **Connect sine to y-coordinate**: On this circle, every point is written as (cos θ, sin θ). So for 150°, we take the y-coordinate: the 1/2 part.
   - board: `sin θ`
4. **Why it is positive**: Now the why: 150° sits in Quadrant II, above the x-axis. Above means y is positive, even though x is negative.
   - board: `above x-axis` · `+ y`
5. **Use the reference angle**: 150° is 30° short of 180°, so its reference angle is 30°. The 30° sine height is 1/2, and Quadrant II keeps it positive.
   - board: `30° back` · `ref angle 30°` · `sin(150°)=1/2`
   - sketch: `flowchart LR ; A[150 degrees] --> B[30 from 180] ; B --> C[reference 30] ; C --> D[sine height 1/2] ; D --> E[Quadrant II positive]`
6. **Final answer**: So the answer is sin(150°) = 1/2. We read sine as the y-coordinate, and the 150° point is above the x-axis.

Missing: point_150: MISSING any: 0 of 3 matched, need 1

## cs_gbn_vs_sr, run 1

Question: "In both timelines frame 2 is damaged. What does the receiver do with the frames that arrive after it, and which frames does the sender retransmit, in (a) Go-Back-N versus (b) Selective Repeat?" (cs_gbn_vs_sr.png)
Score 4/5 (gbn_discards_3_to_8 PASS, gbn_timeout_resends_from_2 PASS, sr_buffers_3_to_5 PASS, sr_nak_only_2 PASS, sr_ack_5 FAIL). Lesson 22.456 s, 6 steps, model gpt-5.5.

**Damaged Frame 2: Go-Back-N vs Selective Repeat**: Both timelines show frame 2 getting damaged, but the receiver’s behavior is different. In Go-Back-N it discards later frames and the sender retransmits the whole run; in Selective Repeat it buffers later frames and the sender retransmits only frame 2.

1. **Find the damaged frame 2 in both timelines**: Great question—both diagrams start the same way: frame 2 is the one hit by error. I’ll circle the error spots, because everything after them shows the protocol difference.
2. **In Go-Back-N, later frames are thrown away**: In Go-Back-N, once frame 2 is missing, the receiver refuses frames 3 through 8 even if they arrive. That’s why I’m boxing the D marks: they mean discarded, not delivered.
   - board: `d: 3–8 thrown away`
3. **Go-Back-N sender retransmits the whole window after timeout**: Now follow the timeout: the sender goes back to frame 2 and resends 2, 3, 4, 5, 6, 7, 8, then continues with 9. So the damaged frame makes the sender repeat everything after it in the window.
   - board: `repeat 2–8`
4. **In Selective Repeat, later frames are kept**: Selective Repeat behaves differently: after the bad frame 2, the receiver keeps frames 3, 4, and 5 in its buffer. It is saying, ‘I’ll save the good ones while I wait for only 2.’
   - board: `stored, not lost`
5. **Selective Repeat retransmits only frame 2**: Look at the sender line after the NAK: it sends frame 2 again, then continues with 6, 7, 8, and onward. The sender retransmits only the damaged frame, because the receiver already saved the later good frames.
   - board: `request only 2`
6. **Answer: discard vs buffer, many repeats vs one repeat**: So the answer is: Go-Back-N discards frames after damaged 2 and retransmits 2 through 8. Selective Repeat buffers frames after damaged 2 and retransmits only 2.
   - sketch: `flowchart LR ; A[Frame 2 damaged] --> B{Protocol?} ; B --> C[Go-Back-N] ; C --> D[Discard later] ; C --> E[Resend 2-8] ; B --> F[Selective Repeat] ; F --> G[Buffer later] ; F --> H[Resend 2]`

Missing: sr_ack_5: MISSING any: 0 of 5 matched, need 1

## cs_gbn_vs_sr, run 2

Question: "In both timelines frame 2 is damaged. What does the receiver do with the frames that arrive after it, and which frames does the sender retransmit, in (a) Go-Back-N versus (b) Selective Repeat?" (cs_gbn_vs_sr.png)
Score 4/5 (gbn_discards_3_to_8 PASS, gbn_timeout_resends_from_2 PASS, sr_buffers_3_to_5 PASS, sr_nak_only_2 PASS, sr_ack_5 FAIL). Lesson 22.207 s, 6 steps, model gpt-5.5.

**Damaged Frame 2: Go-Back-N vs Selective Repeat**: The page compares two sliding-window error-recovery timelines. When frame 2 is damaged, Go-Back-N throws away later out-of-order frames, while Selective Repeat buffers them and retransmits only the missing damaged frame.

1. **Find the damaged frame in both timelines**: Great question—both pictures start the same: frame 2 is damaged. I’ll circle the error spots, then we’ll watch what each receiver does next.
2. **In (a), Go-Back-N discards later arrivals**: In Go-Back-N, the receiver wants frame 2 next. So frames 3 through 8 arrive out of order and get discarded, exactly like this bracket says.
   - board: `d: 3–8 thrown away`
3. **Go-Back-N sender retransmits from frame 2 onward**: Now follow the timeout interval: when the sender times out waiting for Ack 2, it goes back to frame 2. That is why the top line restarts 2, 3, 4, 5, and continues through 9.
   - board: `go back`
4. **In (b), Selective Repeat buffers later frames**: Selective Repeat is pickier: it notices frame 2 is missing, but keeps good later frames. Here frames 3, 4, and 5 are buffered instead of discarded.
   - board: `saved for later`
5. **Selective Repeat retransmits only frame 2**: Look at the Nak 2: the receiver asks for just the damaged frame. The sender retransmits frame 2, then normal new frames 6, 7, 8, and so on continue.
6. **Answer: discard versus buffer**: So the answer is: Go-Back-N discards frames after damaged 2 and retransmits 2 through 8 or 9 as the window continues. Selective Repeat buffers frames after 2 and retransmits only frame 2.
   - board: `? -> d: discard later`
   - sketch: `flowchart LR ; A[Frame 2 damaged] --> B{Protocol?} ; B --> C[Go-Back-N] ; C --> D[Discard later] ; C --> E[Resend 2 onward] ; B --> F[Selective Repeat] ; F --> G[Buffer later] ; F --> H[Resend only 2]`

Missing: sr_ack_5: MISSING any: 0 of 5 matched, need 1

## cs_tcp_handshake, run 1

Question: "Walk me through this TCP three-way handshake: what do the SYN, Seq and Ack values in each of the three segments mean, and why is the first acknowledgement number 1024?" (cs_tcp_handshake.png)
Score 4/5 (client_syn_1023 PASS, server_isn_2131691 PASS, ack_1024_is_1023_plus_1 PASS, final_ack_2131692 PASS, third_seq_1024_established FAIL). Lesson 20.407 s, 6 steps, model gpt-5.5.

**TCP Three-Way Handshake Values**: This page traces a TCP connection setup between client A and server B. We’ll follow the three segments and compute why each acknowledgement number is the next sequence number expected.

1. **Orient: the handshake timeline**: This diagram is a TCP three-way handshake between Client A and Server B. Time flows downward, so we’ll read the three slanted segments from top to bottom.
   - board: `later`
2. **Segment 1: client opens with SYN**: First, A sends SYN=1: that means “I want to start a connection.” Its Seq is 1023, and because no server data is being acknowledged yet, ACK is 0.
   - board: `opens connection`
3. **Why the first Ack Number is 1024**: Here’s the key rule: a SYN consumes one sequence number. So the server acknowledges A’s SYN by saying, “next byte I expect from A is 1024.”
   - board: `+1` · `1023+1=1024`
4. **Segment 2: server replies with SYN-ACK**: Now B also sends its own SYN=1, choosing its own Seq: 2131691. At the same time, ACK=1 with Ack Number 1024 confirms it received A’s SYN.
5. **Segment 3: client acknowledges server**: Finally A sends SYN=0 because it is not starting a new handshake step. Its Seq is 1024, and its Ack Number is 2131692 because B’s SYN also used one sequence number.
   - board: `+1` · `2131691+1`
6. **Recap: what the fields mean**: So the answer is: SYN asks to open, Seq names this side’s starting number, and Ack Number names the next sequence number expected. That’s why the first acknowledgement is 1024: client Seq 1023 plus the SYN’s one slot.
   - sketch: `flowchart TD ; A[A sends SYN] ; B[Seq 1023] ; C[B ACKs 1024] ; D[B sends SYN] ; E[A ACKs 2131692] ; A --> B ; B --> C ; C --> D ; D --> E`

Missing: third_seq_1024_established: MISSING all[1] \| seq is 1024 \| 1024: client seq

## cs_tcp_handshake, run 2

Question: "Walk me through this TCP three-way handshake: what do the SYN, Seq and Ack values in each of the three segments mean, and why is the first acknowledgement number 1024?" (cs_tcp_handshake.png)
Score 5/5 (client_syn_1023 PASS, server_isn_2131691 PASS, ack_1024_is_1023_plus_1 PASS, final_ack_2131692 PASS, third_seq_1024_established PASS). Lesson 19.198 s, 6 steps, model gpt-5.5.

**TCP Three-Way Handshake Values**: This diagram shows TCP’s three-way handshake between client A and server B. The key idea is that SYN consumes one sequence number, so the server acknowledges client Seq 1023 with Ack Number 1024.

1. **Orient: who talks to whom**: We’re walking down time through this handshake: client A sends first, server B replies, then A confirms. I’ll circle the two endpoints and the time direction so the three tilted segments make sense.
   - board: `later`
2. **Segment 1: client opens with SYN**: First, this gray segment is A asking to start a TCP connection. SYN equals 1 means “synchronize,” and Seq 1023 is A’s chosen starting sequence number.
   - board: `A starts at 1023`
3. **Why the first Ack is 1024**: Now follow my arrow to the green reply. A SYN takes up one sequence number, so B answers with Ack Number 1024: “I got 1023; send me 1024 next.”
   - board: `SYN received` · `1023 + 1`
4. **Segment 2: server synchronizes too**: The green segment is doing two jobs at once. B acknowledges A with ACK=1, and B also sends its own SYN with Seq 2131691, choosing its own starting number.
   - board: `B starts here`
5. **Segment 3: client acknowledges server**: Finally A sends the lower gray segment. SYN is now 0 because setup is done on A’s side; Seq becomes 1024, and Ack Number 2131692 acknowledges B’s SYN by adding one.
   - board: `2131691 + 1`
6. **Recap: what the values mean**: So the answer is: SYN announces a starting sequence number, Seq names the sender’s current number, and Ack names the next number expected from the other side. That is why the first acknowledgement is 1024.
   - board: `+1 for SYN`
   - sketch: `flowchart TD ; A[A sends SYN] ; B[B adds 1] ; C[B sends SYN ACK] ; D[A adds 1] ; E[Connection ready] ; A --> B ; B --> C ; C --> D ; D --> E`

## cs_deadlock_rag, run 1

Question: "Is there a deadlock in this resource-allocation graph? R3 has two instances, so does the cycle really mean deadlock?" (cs_deadlock_rag.png)
Score 1/5 (p1_holds_r3_waits_r1 PASS, p2_holds_r1_waits_r2 FAIL, p3_holds_r2_waits_r3 FAIL, cycle FAIL, deadlock_because_no_free_instance FAIL). Lesson 20.125 s, 6 steps, model gpt-5.5.

**Deadlock Check with Multi-Instance R3**: We’ll test the resource-allocation graph by actually satisfying requests and releasing resources. Because R3 has two instances, the visible cycle is not enough by itself to prove deadlock.

1. **Find the possible trouble cycle**: Great question: we’re checking whether this resource-allocation graph is truly deadlocked. I’ll circle the resource boxes and the processes so we can trace who holds what and who is waiting.
2. **Read assignments versus requests**: Remember the rule: resource to process means assigned, process to resource means requested. Follow my arrows: R3 already feeds P1 and P2, while P3 is asking for R3.
   - board: `assigned` · `assigned` · `request`
3. **Simulate who can finish first**: Now we simulate, not just eyeball the cycle. P1 is waiting for R1, but R1 has a free instance because no assignment arrow leaves R1 yet, so grant it and P1 can finish.
   - board: `free now` · `grant R1` · `P1 ✓ releases`
4. **P1’s release breaks the wait**: When P1 finishes, it releases its R3 instance. That gives P3 the R3 it was waiting for, so the cycle is already breakable.
   - board: `release` · `grant R3` · `P3 can run`
5. **Finish the remaining processes**: After P3 runs, it can release R2. Then P2’s request for R2 can be granted, so P2 finishes too: everyone can complete.
   - board: `release R2` · `grant R2` · `P2 ✓`
6. **Answer: cycle but no deadlock**: So the answer is no deadlock. With multiple instances, a cycle is only a warning; here the safe finish order is P1, then P3, then P2.
   - board: `2 copies help`
   - sketch: `flowchart LR ; A[Grant free R1] --> B[P1 finishes] ; B --> C[Release R3] ; C --> D[P3 finishes] ; D --> E[Release R2] ; E --> F[P2 finishes]`

Missing: p2_holds_r1_waits_r2: MISSING all[1] \| p2's request for r2; p3_holds_r2_waits_r3: MISSING all[1] \| p3 is asking for r3; cycle: cycl \| MISSING any: 0 of 13 matched, need 1; deadlock_because_no_free_instance: deadlocked \| MISSING any: 0 of 6 matched, need 1

## cs_deadlock_rag, run 2

Question: "Is there a deadlock in this resource-allocation graph? R3 has two instances, so does the cycle really mean deadlock?" (cs_deadlock_rag.png)
Score 2/5 (p1_holds_r3_waits_r1 PASS, p2_holds_r1_waits_r2 FAIL, p3_holds_r2_waits_r3 PASS, cycle FAIL, deadlock_because_no_free_instance FAIL). Lesson 19.859 s, 6 steps, model gpt-5.5.

**Deadlock with Multiple R3 Instances**: We’ll test the resource-allocation graph, not just spot a cycle. Because R3 has two instances, a cycle is suspicious but not automatically a deadlock; we simulate whether any process can still finish and release resources.

1. **Orient: what the graph means**: Great question: the answer lives in this resource-allocation graph. Green boxes are resource types, orange circles are processes, and the dark dots are resource instances.
   - board: `2 instances`
2. **Decode requests vs assignments**: Follow the arrow direction: process to resource means a request; resource instance to process means an assignment. Here P3 is holding one R2 instance and asking for R3.
   - board: `requests` · `assigned`
3. **Find the apparent cycle**: Now circle the cycle that feels dangerous: P2 asks for R2, R2 is assigned to P3, P3 asks for R3, and R3 is assigned back to P2. That cycle could be trouble.
   - board: `waits` · `held by`
4. **But R3 has another instance**: Here is the key: R3 has two dots, and the left R3 instance is assigned to P1, not inside that P2-P3 cycle. If P1 can finish, it releases R3 and can unblock P3.
   - board: `assigned` · `can finish`
5. **Simulate the release chain**: Run the graph like a safety check: P1 is only waiting for R1, but an R1 instance is already assigned to it, so P1 can complete. Then P1 releases R1 and R3, giving P3 the R3 it requested; P3 finishes and releases R2, so P2 can finish.
   - board: `finish ✓` · `R3 frees` · `R2 frees`
6. **Answer: cycle, but no deadlock**: So the cycle does not force deadlock here. Because R3 has another instance held by P1, and P1 can finish, the graph has a completion order: P1, then P3, then P2.
   - board: `No deadlock` · `then`
   - sketch: `flowchart LR ; A[Find cycle] --> B[Check instances] ; B --> C[P1 finishes] ; C --> D[R3 released] ; D --> E[P3 finishes] ; E --> F[P2 finishes]`

Missing: p2_holds_r1_waits_r2: MISSING all[1] \| p2 asks for r2, r2; cycle: cycl \| MISSING any: 0 of 13 matched, need 1; deadlock_because_no_free_instance: MISSING all[1] \| two dots, and the left r3 instance is assigned \| nother instance held by p1, and p1 can finish

## cs_lru_cache, run 1

Question: "This LRU example has 4 slots and the access sequence A B C D E D F (the number in brackets is the time of last use). Why does E replace A, why does F replace B, and how many hits and misses are there?" (cs_lru_cache.png)
Score 5/5 (e_evicts_a PASS, d_hit_updated PASS, f_evicts_b PASS, six_misses PASS, one_hit PASS). Lesson 18.938 s, 6 steps, model gpt-5.5.

**LRU: Replacing the Oldest Use**: This page shows a 4-slot LRU cache as it processes A B C D E D F. We’ll track the bracketed last-use times to see why E evicts A, why F evicts B, and count hits versus misses.

1. **Orient: four slots, time stamps**: This is an LRU cache trace: four slots hold pages, and the number in brackets is when each page was last used. We’ll follow the access sequence and count hit or miss each time.
   - board: `miss 1`
2. **Fill the empty cache: A, B, C, D**: A, B, C, and D are first-time references, so each is a miss and just fills an empty slot. After D, all four slots are full with last-use times 0, 1, 2, and 3.
   - board: `B miss` · `C miss` · `4 misses`
3. **E replaces A because A is least recent**: Now E is requested and is not in the four slots, so it is a miss. LRU evicts the smallest last-use time: A(0), not B(1), C(2), or D(3), so E enters with time 4.
   - board: `evict oldest` · `miss 5`
4. **D is a hit, so only its time updates**: Next the access is D, and D is already present, so this one is a hit. On an LRU hit, the page stays where it is, but its last-use time updates from 3 to 5.
   - board: `time update` · `hit 1`
5. **F replaces B because B is now least recent**: Finally F is requested and is not in cache, so it is a miss. Compare the times E(4), B(1), C(2), D(5): B has the smallest time, so F replaces B with time 6.
   - board: `evict oldest` · `miss 6`
6. **Answer: 1 hit, 6 misses**: So the answer is: E replaces A because A has the oldest time 0, and F replaces B because B has the oldest time 1 after D’s hit. Total for A B C D E D F is 1 hit and 6 misses.
   - board: `1 hit, 6 misses`
   - sketch: `flowchart LR ; A[Access page] --> B{In cache?} ; B -->\|yes\| C[Hit] ; C --> D[Update time] ; B -->\|no\| E[Miss] ; E --> F[Evict oldest] ; F --> G[Insert page]`

## cs_lru_cache, run 2

Question: "This LRU example has 4 slots and the access sequence A B C D E D F (the number in brackets is the time of last use). Why does E replace A, why does F replace B, and how many hits and misses are there?" (cs_lru_cache.png)
Score 5/5 (e_evicts_a PASS, d_hit_updated PASS, f_evicts_b PASS, six_misses PASS, one_hit PASS). Lesson 16.959 s, 6 steps, model gpt-5.5.

**LRU: Who Gets Replaced?**: We simulate the 4-slot LRU cache on the access sequence A B C D E D F. The item with the smallest bracketed time is least recently used, so it is evicted on a miss when the cache is full.

1. **Orient: brackets are last-use times**: This page is an LRU cache trace for A B C D E D F with 4 slots. I’m circling the first filled slot: the bracket is the time that item was last used.
   - board: `last used at 0`
2. **Fill the 4 slots: A, B, C, D are misses**: Now we load A, then B, then C, then D into empty slots. Each new item is a miss, and its bracket becomes the current time: 0, 1, 2, 3.
   - board: `miss: add B` · `miss: add C`
3. **Why E replaces A**: When E arrives, the cache is full, so LRU picks the smallest time. In A(0), B(1), C(2), D(3), A has the oldest time, so E replaces A.
   - board: `evict oldest` · `miss #5`
4. **D is a hit, so its time updates**: Next access is D, and D is already in cache, so that is a hit. We update only D’s last-use time from 3 to 5.
   - board: `hit: refresh` · `3→5, hit #1`
5. **Why F replaces B**: Now F arrives and the cache is full again: E(4), B(1), C(2), D(5). The smallest time is B(1), so F replaces B.
   - board: `evict oldest` · `miss #6`
6. **Final answer: 1 hit, 6 misses**: So the answer is: E replaces A because 0 is oldest, and F replaces B because 1 is oldest after D refreshes. Total count: 6 misses and 1 hit.
   - board: `hits=1, misses=6`
   - sketch: `flowchart LR ; A[Access item] --> B{In cache?} ; B -->\|yes\| C[Update time] ; B -->\|no\| D{Free slot?} ; D -->\|yes\| E[Place item] ; D -->\|no\| F[Evict oldest] ; F --> E`

## cs_sjf_gantt, run 1

Question: "This chart shows non-preemptive Shortest Job First. Why do P9, P8 and P7 run in that order, why does P12 wait so long, and what is the average waiting time?" (cs_sjf_gantt.png)
Score 2/5 (order_p9_p8_p7 PASS, waits_p7_p8_p9 FAIL, p12_waits_8 PASS, total_33 FAIL, average_2_36 FAIL). Lesson 26.97 s, 6 steps, model gpt-5.5.

**Non‑preemptive SJF on the Gantt Chart**: This chart schedules each batch of arrived processes by shortest burst time, without interrupting a job once it starts. We’ll trace the key choices, explain P9→P8→P7 and P12’s long wait, then compute the average waiting time.

1. **Orient: grey waits, black runs**: This is a non-preemptive Shortest Job First timeline: grey is waiting, black is CPU burst. The answer lives in the black bars and the arrival/burst pairs on the left.
2. **At time 7, choose the shortest burst**: At time 7, P7, P8, and P9 have all arrived. SJF compares their burst times: 3, 2, and 1, so P9 runs first.
   - board: `shortest: 1`
3. **Then P8, then P7**: After P9 finishes at time 10, P8 and P7 are still waiting. The shorter remaining job is P8 with burst 2, then P7 with burst 3.
   - board: `next shortest` · `then longest` · `burst 2` · `burst 3`
4. **Why P12 waits so long**: At time 13, P10, P11, and P12 arrive together. SJF takes burst 1, then 2, so P12’s burst 3 waits behind both before running from 21 to 24.
   - board: `1 then 2` · `wait = 8`
5. **Compute average waiting time**: Now read each grey length: 0,1,2,0,1,3,6,3,0,1,3,8,1,2. Their sum is 31, and 31 divided by 14 gives about 2.21 time units.
   - board: `total wait = 31` · `31/14 = 2.21`
6. **Answer in one picture**: So the order P9, P8, P7 happens because all are ready at 7 and SJF sorts by burst length. P12 waits 8 because two shorter jobs arrived with it; average waiting time is 2.21.
   - board: `1→2→3`
   - sketch: `flowchart LR ; A[Jobs ready] --> B[Compare bursts] ; B --> C[Pick shortest] ; C --> D[Run to finish] ; D --> E[Repeat]`

Missing: waits_p7_p8_p9: MISSING all[1] \| MISSING all[2] \| MISSING all[3]; total_33: MISSING any: 0 of 1 matched, need 1; average_2_36: MISSING any: 0 of 3 matched, need 1

## cs_sjf_gantt, run 2

Question: "This chart shows non-preemptive Shortest Job First. Why do P9, P8 and P7 run in that order, why does P12 wait so long, and what is the average waiting time?" (cs_sjf_gantt.png)
Score 2/5 (order_p9_p8_p7 PASS, waits_p7_p8_p9 PASS, p12_waits_8 FAIL, total_33 FAIL, average_2_36 FAIL). Lesson 24.007 s, 6 steps, model gpt-5.5.

**Non‑preemptive SJF Waiting Times**: This Gantt-style chart shows non-preemptive Shortest Job First: once the CPU picks the shortest available job, it runs that job to completion. We’ll explain the P9→P8→P7 choice, why P12 waits until 21, and compute the average waiting time from the chart.

1. **Orient: SJF chooses among arrived jobs**: This page is a non-preemptive Shortest Job First schedule. I’m circling the process list and the time line because every decision depends on arrival time plus burst time.
   - board: `gray = waiting`
2. **At time 7, the shortest ready job wins**: At time 7, P7, P8, and P9 have all arrived. Their bursts are 3, 2, and 1, so SJF picks P9 first, then P8, then P7.
   - board: `next shortest` · `then`
3. **Run those three choices on the chart**: Let’s do the actual SJF step. P9 runs 9 to 10 after waiting 2, P8 runs 10 to 12 after waiting 3, and P7 runs 12 to 15 after waiting 5.
   - board: `wait = 2` · `wait = 3` · `wait = 5`
4. **Why P12 waits so long**: Now look at time 13: P10, P11, and P12 arrive together. P10 has burst 1, P11 has burst 2, and P12 has burst 3, but P13 and P14 arrive at 17 before P12 gets chosen, and both are shorter.
   - board: `13→21 waits 8`
5. **Compute every waiting time**: For the average, read the gray bars: waiting equals start time minus arrival time. I’ll write the waits beside each batch, then we add them all.
   - board: `0,1,2` · `0,1,3` · `1,2,8,1,2`
6. **Average waiting time result**: Total waiting is 31 over 14 processes, so the average waiting time is 31÷14 = 2.21 time units. Big answer: SJF always picks the shortest arrived job, which can make a longer job like P12 wait.
   - board: `avg = 2.21`
   - sketch: `flowchart LR ; A[Job finishes] --> B[Find arrived] ; B --> C[Pick shortest] ; C --> D[Run to finish] ; D --> E[Record wait] ; E --> B`

Missing: p12_waits_8: MISSING all[1] \| p13 \| p14 \| shorter; total_33: MISSING any: 0 of 1 matched, need 1; average_2_36: MISSING any: 0 of 3 matched, need 1

## math_kinematics, run 1

Question: "For the example at the bottom, how far does the object travel in the 5 seconds? Check it with the v–t graph." (math_kinematics_slide.png)
Score 4/5 (formula FAIL, substitution PASS, final_velocity PASS, distance_25 PASS, graph_area PASS). Lesson 21.285 s, 5 steps, model gpt-5.5.

**Finding Distance from Constant Acceleration**: The bottom example gives u = 0, a = 2 m/s², and t = 5 s. We compute the displacement with the equation s = ut + ½at², then check it as the triangular area under the v–t graph.

1. **Locate the given example**: We’re answering the bottom example: how far in 5 seconds? I’ll circle the given numbers first, then we’ll use the distance equation and check the v–t graph area.
2. **Choose the displacement equation**: Because the question asks distance traveled, we use s, not just final velocity. This equation adds the starting-motion part and the extra distance caused by acceleration.
   - board: `distance formula` · `plug in`
3. **Compute the distance**: Now plug in: s = 0×5 + ½×2×5². The first term is zero, and the acceleration term gives 25 meters.
   - board: `0×5=0` · `½·2·25=25` · `s = 25 m`
4. **Check with the v–t graph**: Now we check it on the graph: displacement is area under the v–t line. Here u = 0, final v = 10 m/s, and time is 5 s, so the area is a triangle.
   - board: `displacement` · `triangle area`
5. **Triangle area confirms it**: The triangle has base 5 s and height 10 m/s. Area = ½×5×10 = 25 m, so the graph agrees: the object travels 25 meters.
   - board: `t: base = 5 s` · `height = 10 m/s` · `½·5·10=25 m`
   - sketch: `flowchart LR ; A[Given u,a,t] --> B[Find final v] ; B --> C[Use s formula] ; C --> D[Check graph area] ; D --> E[25 m]`

Missing: formula: MISSING any: 0 of 3 matched, need 1

## math_kinematics, run 2

Question: "For the example at the bottom, how far does the object travel in the 5 seconds? Check it with the v–t graph." (math_kinematics_slide.png)
Score 4/5 (formula FAIL, substitution PASS, final_velocity PASS, distance_25 PASS, graph_area PASS). Lesson 15.827 s, 5 steps, model gpt-5.5.

**Distance in 5 Seconds**: We use the constant-acceleration equations to find the displacement for the bottom example, then check the same answer as the area under the velocity–time graph.

1. **Where the answer lives**: We’re finding how far the bottom example travels in 5 seconds. I’ll circle the example data, then connect it to the displacement equation and the graph check.
2. **Use the displacement formula**: The distance is displacement s, so we use this equation with u = 0, a = 2, and t = 5. Watch the substitution: the first term disappears because the object starts from rest.
3. **Calculate the displacement**: Now we compute it directly: s = 0·5 + one-half times 2 times 5 squared. That gives 25 metres, so this is our predicted travel distance.
   - board: `s = 25 m` · `substitute`
4. **Check with the graph area**: For a v–t graph, displacement is area underneath. Here velocity rises from 0 to 10 m/s over 5 s, so the shaded triangle area is one-half times base times height.
   - board: `½·5·10 = 25 m`
5. **Final answer**: Both methods agree: the object travels 25 metres in the 5 seconds. The equation gives it, and the graph confirms it as the area under velocity.
   - board: `same s` · `distance = 25 m`
   - sketch: `flowchart LR ; A[Read u,a,t] --> B[Use s formula] ; B --> C[Get 25 m] ; A --> D[Use v-t area] ; D --> C`

Missing: formula: MISSING any: 0 of 3 matched, need 1

## math_ohm_internal_resistance, run 1

Question: "How do we get the 1.5 A current and the 7.5 V across R in this circuit?" (math_ohm_internal_resistance.jpg)
Score 5/5 (total_resistance PASS, current PASS, internal_drop PASS, terminal_voltage PASS, kirchhoff PASS). Lesson 19.89 s, 6 steps, model gpt-5.5.

**Finding Current and Voltage Across R**: This circuit has a 12 V source with two series resistances: internal resistance r = 3 Ω and external resistance R = 5 Ω. The current is found from total series resistance, then the voltage across R is IR = 7.5 V.

1. **Start with the loop**: We’re answering: where do 1.5 A and 7.5 V come from? I’ll circle the single series loop, because the same current flows through both resistors.
2. **Add the series resistances**: In series, resistances add. So the battery pushes through r = 3 ohms plus R = 5 ohms, making 8 ohms total.
   - board: `3+5=8 Ω`
3. **Use Ohm’s law for the current**: Now use Ohm’s law on the whole loop: current equals voltage divided by total resistance. So 12 volts divided by 8 ohms gives 1.5 amps.
   - board: `I=12/8=1.5 A` · `divide by 8Ω`
4. **Voltage across R only**: For the voltage across R, use only the 5 ohm resistor. Multiply the shared current, 1.5 A, by R = 5 ohms, and you get 7.5 volts.
   - board: `1.5×5=7.5 V` · `V=IR`
5. **Check the voltage split**: The internal resistor also uses up voltage: 1.5 A times 3 ohms equals 4.5 V. The two drops, 4.5 V and 7.5 V, add back to the 12 V source.
   - board: `4.5+7.5=12`
6. **Answer in one chain**: So the current is 1.5 A because the total resistance is 8 ohms. Then the voltage across R is 7.5 V because that same current flows through the 5 ohm resistor.
   - sketch: `flowchart LR ; A[12 V source] --> B[3Ω + 5Ω] ; B --> C[8Ω total] ; C --> D[I = 1.5 A] ; D --> E[Across 5Ω] ; E --> F[7.5 V]`

## math_ohm_internal_resistance, run 2

Question: "How do we get the 1.5 A current and the 7.5 V across R in this circuit?" (math_ohm_internal_resistance.jpg)
Score 5/5 (total_resistance PASS, current PASS, internal_drop PASS, terminal_voltage PASS, kirchhoff PASS). Lesson 15.719 s, 6 steps, model gpt-5.5.

**Finding Current and Voltage Across R**: The circuit has a 12 V battery with internal resistance 3 Ω in series with an external 5 Ω resistor. Use total series resistance to get the 1.5 A current, then Ohm’s law on R to get 7.5 V.

1. **What we are solving**: We want the current and the voltage across this outside resistor. I’ll circle R first, because the 7.5 V question belongs exactly there.
2. **Add the series resistances**: The battery’s internal resistance r and the outside resistor R are in one loop, so the same current goes through both. Series resistances add: 3 Ω plus 5 Ω gives 8 Ω total.
   - board: `3+5=8 Ω`
3. **Use the battery emf**: Now use the 12 V source to push current through that total 8 Ω. Ohm’s law for the whole loop is I equals 12 divided by 8, which is 1.5 A.
   - board: `I=V/R` · `12÷8=1.5 A`
4. **Voltage across external R**: For the voltage across R only, use the same current through the 5 Ω resistor. So IR is 1.5 times 5, giving 7.5 V.
   - board: `same I` · `1.5×5=7.5 V`
5. **Where the missing voltage goes**: The full 12 V is split between the two series resistances. The internal 3 Ω takes 4.5 V, and the outside 5 Ω takes 7.5 V; together they add back to 12 V.
   - board: `4.5+7.5=12`
   - sketch: `flowchart LR ; A[12 V emf] --> B[Add resistors] ; B --> C[3+5=8 Ω] ; C --> D[I=12/8] ; D --> E[1.5 A] ; E --> F[VR=I×5]`
6. **Answer in one line**: So the page’s numbers come straight from series resistance and Ohm’s law. Current is 1.5 A, and the voltage across R is 7.5 V.

## math_parallel_meters, run 1

Question: "Suppose the battery gives 12 V, R1 = 4 Ω, R2 = 2 Ω and R3 = 4 Ω. What do the ammeters A1, A2, A3 and the voltmeters V3 and V4 read?" (math_parallel_meters.png)
Score 5/5 (topology PASS, a2_r1_branch PASS, a3_r2r3_branch PASS, a1_total PASS, v3_v4_split PASS). Lesson 18.414 s, 6 steps, model gpt-5.5.

**Circuit Meter Readings**: This circuit has a 12 V supply feeding parallel branches: one branch contains R1, and the lower branch contains R2 and R3 in series. We compute branch currents first, then use series voltage division for V3 and V4.

1. **Orient the circuit**: We’re answering the meter question by treating the battery as 12 volts across these two rails. I’ll circle the source and the two resistor paths where the readings come from.
2. **Use the 12 V across each branch**: Because the R1 branch and the lower branch connect across the same left and right rails, each branch gets the full 12 volts. So V2 would be 12 volts across R1, even before finding currents.
   - board: `12 V` · `12 V` · `across R1`
3. **Find A2 through R1**: Now run Ohm’s law on R1: current is voltage divided by resistance. For R1, that is 12 divided by 4, so A2 reads 3 amps.
   - board: `12/4 = 3 A` · `A2 = 3 A`
4. **Find lower-branch current A3**: The bottom path has R2 and R3 in series, so their resistances add. That makes 2 plus 4 equals 6 ohms, and 12 divided by 6 gives A3 as 2 amps.
   - board: `2+4=6 Ω` · `A3 = 2 A`
5. **Add currents for A1**: A1 sits before the current splits, so it reads the total current supplied by the battery. Add the two branch currents: 3 amps plus 2 amps equals 5 amps.
   - board: `3 A` · `2 A` · `A1 = 5 A`
6. **Split voltage over R2 and R3**: Finally, V3 and V4 measure voltage drops in the same 2 amp series branch. So R2 drops 2 times 2 equals 4 volts, and R3 drops 2 times 4 equals 8 volts.
   - board: `V3 = 4 V` · `V4 = 8 V`
   - sketch: `flowchart LR ; A[12 V supply] --> B[parallel branches] ; B --> C[R1: 4 ohm] ; B --> D[R2+R3: 6 ohm] ; C --> E[A2 = 3 A] ; D --> F[A3 = 2 A] ; E --> G[A1 = 5 A] ; F --> G`

## math_parallel_meters, run 2

Question: "Suppose the battery gives 12 V, R1 = 4 Ω, R2 = 2 Ω and R3 = 4 Ω. What do the ammeters A1, A2, A3 and the voltmeters V3 and V4 read?" (math_parallel_meters.png)
Score 5/5 (topology PASS, a2_r1_branch PASS, a3_r2r3_branch PASS, a1_total PASS, v3_v4_split PASS). Lesson 19.101 s, 6 steps, model gpt-5.5.

**Parallel Branch Currents and Series Voltage Drops**: The battery places 12 V across two parallel branches: one branch has R1 alone, and the other has R2 and R3 in series. So we calculate each branch current, then split the 12 V across R2 and R3.

1. **Find the circuit structure**: We’re answering the meter readings by first spotting the two parallel paths across the 12 V battery. I’ll circle the source and box the lower series branch where V3 and V4 live.
   - board: `2Ω + 4Ω`
2. **Use the 12 V across each branch**: Because these branches connect between the same left and right rails, each whole branch gets the full 12 V. So R1 has 12 V, and the R2-plus-R3 branch also has 12 V.
   - board: `12 V` · `12 V` · `V=12 V`
3. **Compute A2 through R1**: Now use Ohm’s law on the middle branch: current through R1 is 12 divided by 4. That gives 3 A, so ammeter A2 reads 3 A.
   - board: `I=12/4=3A` · `A2 = 3 A`
4. **Compute lower-branch current**: For the bottom path, R2 and R3 are in series, so their resistances add: 2 plus 4 is 6 ohms. The branch current is 12 divided by 6, so A3 reads 2 A.
   - board: `R=6Ω` · `A3 = 2 A`
5. **Get V3 and V4 drops**: The same 2 A flows through both bottom resistors. So V3 across R2 is 2 times 2, and V4 across R3 is 2 times 4.
   - board: `V3 = 4 V` · `V4 = 8 V`
6. **Finish with total current A1**: A1 sits before the split, so it reads the total current from both branches. Add 3 A and 2 A: the final readings are A1 5 A, A2 3 A, A3 2 A, V3 4 V, and V4 8 V.
   - board: `3A+2A=5A`
   - sketch: `flowchart TD ; A[12 V source] --> B[Parallel branches] ; B --> C[R1: 4 ohm] ; B --> D[R2+R3: 6 ohm] ; C --> E[A2 = 3 A] ; D --> F[A3 = 2 A] ; E --> G[A1 = 5 A] ; F --> G`

