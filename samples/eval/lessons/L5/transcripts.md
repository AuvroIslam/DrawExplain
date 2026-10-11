# Lesson transcripts: L5

Backend f237da8 (Add README with pipeline and results) + uncommitted changes. + measured colours in the region list, read-the-page rule.
Every lesson of the benchmark, as the student hears it (narration) and sees it (board text, sketch), with the automatic checks. Board texts attached to a lettered node show the letter first. Made by backend/scripts/eval_lessons.py.

## dijkstra_AtoE, run 1

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 5/5 (init PASS, relax_A PASS, relax_I_all PASS, order PASS, answer PASS). Lesson 24.16 s, 6 steps, model gpt-5.5.

**Shortest Path from A to E**: We’ll run Dijkstra’s algorithm on the graph shown, starting at A and stopping when E is finalized. The shortest path will come from the tentative-distance updates we write beside the vertices.

1. **Orient: start at A, target E**: You’re asking for the shortest path from A to E. This page is Dijkstra’s algorithm, so we’ll start at the left-middle A and stop when the lower-right E becomes final.
   - board: `a: A = 0 start`
2. **Iteration 1: finalize A**: Dijkstra first picks the unvisited vertex with smallest tentative distance, so A at 0 is final. From A, we write the first distances to its neighbors: B, G, H, and I.
   - board: `a: 0 ✓` · `b: B ∞→5` · `g: G ∞→9` · `h: H ∞→18`
3. **Finish A’s relaxations**: One more neighbor of A matters a lot: the center I gets distance 1 through the edge labeled 1. That tiny cost makes I the next vertex Dijkstra will choose.
   - board: `I ∞→1` · `a -> ?: cost 1`
4. **Iteration 2: finalize I**: Now the smallest unvisited tentative distance is I at 1, so I becomes final. Relaxing I improves C to 7, E to 3, and G from 9 down to 4.
   - board: `1 ✓` · `c: C ∞→7` · `e: E ∞→3` · `g: G 9→4`
5. **Iteration 3: finalize E and stop**: Now E has the smallest unvisited distance, 3, so Dijkstra finalizes E. Because E is our target, we stop: trace predecessors backward, E came from I, and I came from A.
   - board: `e: 3 ✓ final` · `? -> e: cost 2` · `a -> ?: cost 1`
6. **Answer: A → I → E**: So the shortest path is A to I to E, with total cost 1 plus 2 equals 3. The key Dijkstra idea is: always finalize the smallest tentative distance, then relax its outgoing edges.
   - board: `e: 1+2=3`
   - sketch: `flowchart LR ; A[Start A=0] --> Pick[Pick smallest] ; Pick --> Relax[Relax edges] ; Relax --> E{E final?} ; E -->\|no\| Pick ; E -->\|yes\| Path[A-I-E cost 3]`

## tcp_cwnd, run 1

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 5/5 (starts_at_1 PASS, doubling PASS, concrete_threshold PASS, additive PASS, timeout PASS). Lesson 24.153 s, 6 steps, model gpt-5.5.

**TCP CongWin Until Timeout**: This page gives the three TCP congestion-window rules: slow start, additive increase, and multiplicative decrease. Using an example with ssthresh = 8 MSS, we trace CongWin from 1 MSS up to a timeout, then show the reset.

1. **Where the answer lives**: This page answers how CongWin grows, then drops when loss happens. I’ll use the rules here with an example threshold of 8 MSS, starting at the Slow Start rule.
   - board: `example: ssthresh=8`
2. **Slow Start doubles each RTT**: In Slow Start, each ACK adds 1 MSS, so across a whole round trip the window doubles. From 1 MSS, our example goes 1 to 2 to 4 to 8, stopping when it hits the threshold.
   - board: `cwnd 1→2→4→8` · `until threshold`
3. **Then additive increase takes over**: Once CongWin reaches the threshold, TCP switches to congestion avoidance. Now growth is gentler: about +1 MSS per RTT, so 8 becomes 9, then 10, 11, and 12.
   - board: `cwnd 8→9→10→11→12` · `after that`
4. **Timeout cuts the window**: At round 8 in our example, CongWin is 12 MSS and a timeout occurs. The multiplicative decrease rule halves the threshold to 6, but resets CongWin all the way to 1 MSS.
   - board: `12/2=6; cwnd=1`
5. **After timeout, Slow Start restarts**: After that reset, TCP starts slow start again, now aiming for the new threshold 6. So the next rounds go 1 to 2 to 4 to 6, capped at the new ssthresh.
   - board: `restart SS` · `new ssthresh=6` · `after timeout: 1→2→4→6`
6. **The full answer**: So, in this example, CongWin is 1, 2, 4, 8, 9, 10, 11, 12, then timeout resets it to 1. Big idea: exponential growth first, linear growth next, sharp cut on timeout.
   - board: `1,2,4,8,9,10,11,12,1`
   - sketch: `flowchart LR ; A[Start cwnd 1] ; B[Slow Start] ; C[Hit ssthresh] ; D[Additive Increase] ; E[Timeout] ; F[Reset cwnd 1] ; A --> B ; B --> C ; C --> D ; D --> E ; E --> F`

## flowchart_invalid_twice, run 1

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 23.563 s, 6 steps, model gpt-5.5.

**Invalid Twice in the Validation Loop**: This flowchart keeps reading input until the decision box says it is valid. If the input is invalid twice, the chart follows the “No” loop twice before it can move on.

1. **Find the loop that matters**: Great question: invalid twice means we watch the loop around this decision. I’ll circle the main check, because every input must pass through Valid? before the chart can end.
2. **First invalid input**: On the first try, the input is not valid, so we take the red No path downward. That sends us to Show error, not to Process data.
   - board: `invalid` · `1st error shown`
3. **Loop back to ask again**: After the error, the arrow loops back to Read input. So the user gets another chance instead of the program stopping.
   - board: `try again` · `2nd attempt starts`
4. **Second invalid input**: If the second input is invalid too, the exact same No path happens again. We show the error a second time, then loop back to Read input again.
   - board: `invalid again` · `2nd error shown` · `ask again`
5. **When it finally becomes valid**: Only when Valid? answers Yes do we leave the loop. Then the flow goes to Process data and finally End.
   - board: `passes` · `finish`
6. **Answer: invalid twice repeats twice**: So, invalid twice means: error, retry, error, retry. The loop keeps doing that until a later input is valid; it does not process data yet.
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`

## cs_bfs_dfs, run 1

Question: "In which order does breadth-first search visit the nodes if it starts at A and takes neighbours in alphabetical order? How would depth-first search from A differ?" (cs_bfs_dfs.png)
Score 5/5 (bfs_order PASS, bfs_queue PASS, bfs_levels PASS, dfs_order PASS, dfs_mechanism PASS). Lesson 20.105 s, 6 steps, model gpt-5.5.

**BFS vs DFS from A**: We will run breadth-first search on the shown graph starting at A, taking neighbours alphabetically. Then we will contrast it with how depth-first search dives down one branch before backing up.

1. **Start at A**: This graph question lives at the top: start at A. For breadth-first search, I mark A as seen immediately and put it in the FIFO queue.
   - board: `a: seen; Q=[A]`
2. **Visit A, enqueue level 1**: Now we dequeue A and visit it. Alphabetical neighbours from A are B, C, then E, so those three join the back of the queue as level 1.
   - board: `a: 1 ✓` · `b: seen L1, p=A` · `c: seen L1, p=A` · `e: seen L1, p=A`
3. **Visit B, enqueue D and F**: The FIFO rule says B is next, because it has waited longest. Visiting B discovers its unvisited alphabetical neighbours D and F, making the queue C, E, D, F.
   - board: `b: 2 ✓` · `d: seen L2, p=B` · `f: seen L2, p=B`
4. **Visit C, enqueue G**: Next out of the queue is C. Its unvisited alphabetical neighbour is G, so G is added after D and F: the queue becomes E, D, F, G.
   - board: `c: 3 ✓` · `g: seen L2, p=C`
5. **Finish the BFS queue**: Now no new vertices are discovered. FIFO simply visits E, then D, then F, then G, emptying the queue.
   - board: `e: 4 ✓` · `d: 5 ✓` · `f: 6 ✓` · `g: 7 ✓`
6. **DFS differs by diving**: So BFS visits A, B, C, E, D, F, G. Depth-first search with the same alphabetical rule would dive A to B to D first, then backtrack: A, B, D, F, E, C, G.
   - board: `a -> b: DFS dives` · `b -> d: first branch` · `a+b+c+e+d+f+g: BFS: level order`
   - sketch: `flowchart TD ; A[Start A] --> B[Queue FIFO] ; B --> C[Visit front] ; C --> D[Add unseen] ; D --> E[Alphabetical] ; E --> F[Queue empty?] ; F -->\|no\| C ; F -->\|yes\| G[Order done]`

## math_pythagoras, run 1

Question: "How does this picture prove the Pythagorean theorem?" (math_pythagoras_squares.jpg)
Score 5/5 (areas PASS, sides_3_4_5 PASS, sum_9_16_25 PASS, theorem PASS, rearrangement PASS). Lesson 17.639 s, 5 steps, model gpt-5.5.

**Pythagoras by Rearranging Area**: This picture proves the Pythagorean theorem by showing three squares built on the sides of a right triangle. The small red and yellow unit squares tile the outside squares, and the rearranged area matches the square on the slanted side.

1. **Find the right triangle**: This proof lives around the pale green triangle in the middle. I’m circling it first: its sides touch the red square on the left, the yellow square below, and the tilted square on the slanted side.
   - board: `right triangle`
2. **The two leg-squares**: Now look at the two straight-leg squares. The red square on the left is built on the vertical side, and the yellow square below is built on the bottom side of the same triangle.
   - board: `area = a²` · `area = b²`
3. **Their areas are countable tiles**: The grid makes the areas visible. The left red square is four by four, so it has 16 red unit squares; the bottom yellow square is three by three, so it has 9 yellow unit squares.
   - board: `4×4 = 16` · `3×3 = 9` · `16 + 9 = 25`
4. **The slanted-side square**: Follow my arrow to the tilted square on the triangle’s slanted side. Its red middle and yellow border are the same 25 unit squares, rearranged into one square.
   - board: `rearrange` · `area = c² = 25`
5. **Why that proves it**: So the two leg-squares together fill exactly the square on the slanted side. That is the Pythagorean theorem: a² plus b² equals c².
   - board: `same area` · `a² + b² = c²`
   - sketch: `flowchart LR ; A[Left square a²] --> C[Add areas] ; B[Bottom square b²] --> C ; C --> D[Same 25 tiles] ; D --> E[Slanted square c²] ; E --> F[a²+b²=c²]`

## math_quadratic, run 1

Question: "Where does this parabola cross the x-axis? Solve its equation step by step." (math_quadratic_roots.png)
Score 5/5 (set_zero PASS, method PASS, root_2 PASS, root_minus_1 PASS, graph_link PASS). Lesson 19.2 s, 5 steps, model gpt-5.5.

**Finding the x-intercepts**: We solve where the red parabola crosses the x-axis by setting y = 0 in the printed equation. Factoring gives the two crossing points visible on the graph: x = -1 and x = 2.

1. **The crossings live on the x-axis**: We’re finding where the red parabola crosses the x-axis. I’ll circle the two red crossing spots, then we’ll prove those x-values from the equation.
2. **Set y equal to zero**: On the x-axis, the height is zero, so y becomes 0. That turns the printed equation into 0 = x² - x - 2.
   - board: `y = 0 here` · `0 = x² - x -`
3. **Factor the quadratic**: Now factor x² - x - 2. We need two numbers that multiply to -2 and add to -1: those are -2 and +1.
   - board: `(x - 2)(x + 1)` · `product -2, sum -1`
4. **Use zero product rule**: If the product is zero, one factor must be zero. So x - 2 = 0 gives x = 2, and x + 1 = 0 gives x = -1.
   - board: `x = 2` · `x = -1` · `zeros`
5. **Answer: two x-intercepts**: So the parabola crosses the x-axis at x = -1 and x = 2. As points, the x-intercepts are (-1, 0) and (2, 0).
   - board: `(-1,0), (2,0)`
   - sketch: `flowchart TD ; A[Set y=0] --> B[Factor quadratic] ; B --> C[Zero product] ; C --> D[x=-1] ; C --> E[x=2]`

## cs_sjf_gantt, run 1

Question: "This chart shows non-preemptive Shortest Job First. Why do P9, P8 and P7 run in that order, why does P12 wait so long, and what is the average waiting time?" (cs_sjf_gantt.png)
Score 4/5 (order_p9_p8_p7 PASS, waits_p7_p8_p9 PASS, p12_waits_8 FAIL, total_33 PASS, average_2_36 PASS). Lesson 31.648 s, 6 steps, model gpt-5.5.

**Non-Preemptive SJF: Why This Order?**: This chart is a non-preemptive Shortest Job First schedule: whenever the CPU becomes free, it chooses the ready process with the smallest burst time and runs it to completion. Using the printed arrivals and bursts, the waiting times add to 33, so the average waiting time is 33/14 = 2.36.

1. **Orient: the rule and the target cluster**: We’re answering your question with the SJF rule: at each free time, pick the ready process with the shortest burst. The key cluster is P9, P8, P7 around time 9 to 15.
   - board: `choose only when free`
2. **Run up to the P7/P8/P9 decision**: First the CPU clears the earlier arrivals in order: P1, P2, P3, then P4, P5, P6. Notice P6 is non-preemptive, so even when P7, P8, and P9 arrive at 7, P6 keeps running until 9.
   - board: `waits: 0,1,2,0,1,3` · `keeps CPU`
3. **Why P9, then P8, then P7**: At time 9, all three are ready: P7 has burst 3, P8 has burst 2, and P9 has burst 1. So SJF picks P9 first, then P8, and P7 last.
   - board: `P9 9-10, wait 2` · `P8 10-12, wait 3` · `P7 12-15, wait 5` · `1, then 2, then 3`
4. **Why P12 waits so long**: Now watch P12: it arrives at 13, but at time 15 shorter ready jobs are chosen first. P10 runs, then P11; later P13 and P14 also beat P12 because their bursts are shorter.
   - board: `P10 wait 2; P11 wait 3` · `P13 wait 1; P14 wait 2` · `waits 13→21`
5. **Compute the average waiting time**: Let’s add the waiting times from the simulated schedule. The total wait is 33 across 14 processes, so the average waiting time is 33 divided by 14, which is 2.36.
   - board: `Σ wait = 33` · `33 ÷ 14 = 2.36`
6. **Recap: the answer plainly**: So P9, P8, P7 run in that order because at time 9 their bursts are 1, 2, and 3. P12 waits until 21 because shorter ready jobs keep being selected, and the average waiting time is 2.36.
   - sketch: `flowchart LR ; A[CPU free] --> B[Find ready jobs] ; B --> C[Pick shortest burst] ; C --> D[Run to finish] ; D --> E[Record wait] ; E --> A`

Missing: p12_waits_8: MISSING all[1] \| p13 \| p14 \| shorter

