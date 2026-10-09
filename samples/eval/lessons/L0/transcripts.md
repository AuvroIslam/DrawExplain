# Lesson transcripts: L0

Backend 3da1980 (Add PDF reader mode with page context). teach-by-doing rule only (no simulation rule).
Every lesson of the benchmark, as the student hears it (narration) and sees it (board text, sketch), with the automatic checks. Board texts attached to a lettered node show the letter first. Made by backend/scripts/eval_lessons.py.

## dijkstra_AtoE, run 1

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 2/5 (init FAIL, relax_A PASS, relax_I_all FAIL, order FAIL, answer PASS). Lesson 20.606 s, 5 steps, model gpt-5.5.

**Shortest Path from A to E**: This page sets up Dijkstra’s algorithm on a weighted graph. To answer your question, we trace from A toward E by repeatedly keeping the cheapest known distance and improving neighbors.

1. **Find the problem on the graph**: You asked how to get the shortest path from A to E; that answer lives in this weighted graph. I’ll circle A as the source and E as the destination we’re trying to reach.
2. **Initialize distances from A**: Dijkstra starts with A at distance zero. From A, the first possible costs are B = 5, I = 1, G = 9, and H = 18, so I is the cheapest next step.
   - board: `a: dist = 0` · `a -> ?: cost 1` · `best so far`
3. **Relax through I**: Now we lock in I with total distance 1. From I to E costs 2 more, so A to I to E gives 1 + 2 = 3, which is already very strong.
   - board: `? -> e: +2` · `e: dist = 3`
4. **Check if anything beats 3**: Dijkstra still checks other unsettled routes, because a later path might beat E’s current 3. But the next cheapest alternatives from A are B at 5 and G at 4 through I, both already exceed 3 before reaching E.
   - board: `a -> b: 5` · `? -> g: 1+3=4` · `e: smaller wins`
5. **Answer: A → I → E**: So the shortest path from A to E on this page is A to I to E, with total cost 3. The key Dijkstra idea is: always expand the smallest known distance next.
   - board: `a -> ?: 1` · `? -> e: +2` · `a+e: total = 3`
   - sketch: `flowchart LR ; A[Start A] --> B[Pick smallest] ; B --> C[Relax neighbors] ; C --> D[Update distances] ; D --> E[Reach E] ; E --> F[Path cost 3]`

Missing: init: MISSING \| a: dist = 0; relax_I_all: MISSING \| MISSING \| e gives 1 + 2 = 3; order: I settled: lock in i \| E final: MISSING

## dijkstra_AtoE, run 2

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 2/5 (init FAIL, relax_A FAIL, relax_I_all FAIL, order PASS, answer PASS). Lesson 15.304 s, 5 steps, model gpt-5.5.

**Shortest Path from A to E**: We’ll use the graph on this page to trace Dijkstra’s idea from source A toward destination E. The key is to keep the cheapest known distance so far, then expand through the smallest unfinished node.

1. **Find the start and goal**: Your question is: how do we get from A to E cheapest? I’ll circle the source A in blue and the destination E in green so every step has a clear start and finish.
2. **Start with A’s direct options**: From A, Dijkstra first writes down direct costs to neighbors. The best-looking move is A to I with cost 1, much cheaper than A to B, G, or H.
   - board: `a -> ?: cost 1` · `dist = 1`
3. **Relax through I toward E**: Now expand I, because its distance 1 is the smallest unfinished distance. From I to E costs 2 more, so A to I to E totals 1 plus 2 equals 3.
   - board: `? -> e: +2` · `e: 1 + 2 = 3`
4. **Check if another route can beat 3**: Dijkstra does not stop at a guess; it asks whether any unfinished route can beat 3. Since all edge weights are non-negative, once E has the smallest tentative distance, 3 is locked in.
   - board: `e: locked: 3`
5. **Answer: A → I → E**: So the shortest path from A to E is A to I to E, total cost 3. Follow the green arrows: Dijkstra found E by expanding the cheapest frontier first.
   - board: `a -> ?: 1` · `? -> e: 2` · `a+e: shortest = 3`
   - sketch: `flowchart LR ; A[A dist 0] --> I[I dist 1] ; I --> E[E dist 3] ; E --> Done[Path locked]`

Missing: init: MISSING \| a dist 0; relax_A: MISSING \| MISSING \| MISSING \| i with cost 1; relax_I_all: MISSING \| MISSING \| e totals 1 plus 2 equals 3

## dijkstra_AtoE, run 3

Question: "how to get the shortest path from A to E" (dijkstra-slides.pdf, page 3)
Score 3/5 (init FAIL, relax_A PASS, relax_I_all FAIL, order PASS, answer PASS). Lesson 17.734 s, 5 steps, model gpt-5.5.

**Shortest path from A to E**: We’ll answer the student’s question by tracing Dijkstra’s algorithm on this graph, starting at A and stopping once E’s cheapest distance is confirmed. The key idea is: always expand the unvisited vertex with the smallest known distance, then improve its neighbors.

1. **Orient: start at A, aim for E**: This page is a Dijkstra trace graph; to get from A to E, I’ll mark A as our source and E as our target. We are hunting the cheapest total weight, not the fewest edges.
   - board: `a: dist=0`
2. **Initialize A’s direct neighbors**: From the source A, write down the first tentative distances to every neighbor. These are just one-edge costs: A to I is already very promising at 1.
   - board: `a -> ?: +1` · `dist=1` · `a -> b: +5` · `a -> g: +9`
3. **Expand I: improve E through I**: Dijkstra next picks I because 1 is the smallest tentative distance. From I, going to E adds 2, so A to I to E totals 3.
   - board: `? -> e: +2` · `e: 1+2=3`
4. **Check competitors before finalizing E**: Now E has tentative distance 3. Any other way must come from an unvisited vertex with distance at least 4 or 5, so none can beat 3 before E is chosen.
   - board: `e: best so far` · `g: via I: 4`
5. **Answer: shortest path A → I → E**: So the shortest path from A to E is A to I to E, with total cost 3. Dijkstra works because the smallest tentative vertex becomes permanent before any longer route can undercut it.
   - board: `a -> ?: +1` · `? -> e: +2` · `e: shortest = 3`
   - sketch: `flowchart LR ; A[Start A] --> N[Set distances] ; N --> S[Pick smallest] ; S --> U[Update neighbors] ; U --> Q{Reached E?} ; Q -->\|no\| S ; Q -->\|yes\| P[Path A-I-E]`

Missing: init: MISSING \| a: dist=0; relax_I_all: MISSING \| MISSING \| e totals 3

## tcp_cwnd, run 1

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 4/5 (starts_at_1 PASS, doubling PASS, concrete_threshold FAIL, additive PASS, timeout PASS). Lesson 16.325 s, 6 steps, model gpt-5.5.

**CongWin: Start to Timeout**: This page shows the TCP congestion window’s path: begin at 1 MSS, grow fast in Slow Start, then grow gently in Additive Increase, and finally drop on a timeout by Multiplicative Decrease.

1. **Find the whole path**: Great question: from the start until a timeout, CongWin follows these three stages. I’m circling the three stage names so we can read the window’s story top to bottom.
2. **Start at one MSS**: At the very start, TCP sets CongWin to exactly 1 MSS. That is the tiny launch point before any ACKs have helped it grow.
   - board: `launch size`
3. **ACKs make Slow Start grow fast**: During Slow Start, every successful ACK increases cwnd by 1. Because a larger window creates more ACKs per round, this looks exponential until the threshold is reached.
   - board: `1, 2, 4, 8...`
4. **At threshold, growth becomes gentle**: When CongWin reaches the threshold, TCP leaves Slow Start and switches to Additive Increase. Now each ACK adds only 1 over n, so the window climbs roughly one MSS per RTT instead of doubling.
   - board: `switch here` · `linear climb`
5. **A timeout cuts the window**: Now the timeout answers the last part of your question. On timeout, TCP sets the threshold to half the old CongWin, then resets CongWin all the way back to 1 MSS.
6. **Plain answer recap**: So the path is: start at 1 MSS, grow exponentially until threshold, grow additively after that, and on timeout drop to 1 MSS while the new threshold becomes half the previous CongWin.
   - board: `grow then reset`
   - sketch: `flowchart TD ; A[Start 1 MSS] ; B[Slow Start] ; C[Hit threshold] ; D[Additive Increase] ; E[Timeout] ; F[CongWin 1 MSS] ; A --> B ; B --> C ; C --> D ; D --> E ; E --> F`

Missing: concrete_threshold: MISSING

## tcp_cwnd, run 2

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 4/5 (starts_at_1 PASS, doubling PASS, concrete_threshold FAIL, additive PASS, timeout PASS). Lesson 18.678 s, 7 steps, model gpt-5.5.

**TCP Congestion Window Until Timeout**: This slide answers how CongWin grows first fast, then gently, and finally drops when a timeout signals congestion. The key path is: Slow Start → Additive Increase → Multiplicative Decrease on timeout.

1. **Find the growth-and-drop story**: Great question: from the start until a timeout, CongWin follows these three rules. I’ll circle the main title, then we’ll walk down the slide like a timeline.
2. **Start at 1 MSS**: At the very beginning, Slow Start sets CongWin to one segment. That tiny starting window is cautious: TCP probes the network before sending a lot.
   - board: `cwnd = 1 MSS`
3. **Slow Start grows exponentially**: Now each ACK makes CongWin increase by 1. Because a larger window creates more ACKs per round trip, the total window roughly doubles each RTT until the threshold.
   - board: `1→2→4→8`
4. **Threshold changes the mode**: The phrase 'until the threshold value' is the switch point. After that, TCP leaves Slow Start and uses Additive Increase, which grows much more carefully.
   - board: `hit threshold`
5. **Additive Increase grows linearly**: In Additive Increase, each ACK adds only 1 over n, where n is the current CongWin. So across one RTT, all those tiny pieces add up to about one MSS total.
   - board: `+1 MSS per RTT`
6. **Timeout causes the drop**: Now we reach the timeout case. On timeout, TCP treats the network as congested: it halves the threshold, then resets CongWin all the way back to 1 MSS.
7. **Plain answer**: So the answer is: CongWin starts at 1 MSS, grows exponentially in Slow Start, then linearly in Additive Increase, and a timeout drops it to 1 MSS while setting the threshold to half the old CongWin.
   - board: `grow then switch` · `reset cwnd`
   - sketch: `flowchart LR ; A[Start 1 MSS] --> B[Slow Start] ; B --> C[Threshold hit] ; C --> D[Additive Increase] ; D --> E[Timeout] ; E --> F[CongWin 1 MSS]`

Missing: concrete_threshold: MISSING

## tcp_cwnd, run 3

Question: "How does the congestion window change from the start until a timeout?" (L11 TCP Error Control & Congestion Control.pptx.pdf, page 31)
Score 3/5 (starts_at_1 PASS, doubling FAIL, concrete_threshold FAIL, additive PASS, timeout PASS). Lesson 19.209 s, 7 steps, model gpt-5.5.

**CongWin from start to timeout**: This page says TCP first grows CongWin quickly with Slow Start, then more gently with Additive Increase, and when a timeout happens it cuts down hard. The key timeline is: start at 1 MSS, grow to the threshold, switch growth mode, then timeout resets CongWin to 1 MSS and sets a new threshold at half the old CongWin.

1. **Find the timeline**: Your question is the story from start until a timeout. I’ll circle the three stages: Slow Start, Additive Increase, then Multiplicative Decrease when loss is detected.
2. **Start at 1 MSS**: At the very beginning, CongWin is tiny: exactly 1 MSS. That keeps TCP cautious before it knows how much the network can handle.
   - board: `cwnd starts small`
3. **Slow Start grows fast**: During Slow Start, every successful ACK adds 1 to cwnd. Because a bigger window creates more ACKs per round trip, this is why the slide calls it exponential increase.
   - board: `doubles per RTT`
4. **Threshold changes the mode**: Slow Start does not continue forever; it stops when CongWin reaches the threshold value. After that, TCP switches to Additive Increase, so growth becomes gentle instead of explosive.
   - board: `until threshold`
5. **Additive Increase crawls upward**: Here n means the current CongWin size, so each ACK adds only 1/n of a segment. Across about n ACKs in one RTT, that totals roughly +1 MSS per RTT.
   - board: `+1 MSS/RTT`
6. **Timeout cuts it down**: Now we hit your endpoint: if a timeout occurs, TCP treats it as serious congestion. The threshold becomes half of the old CongWin, and CongWin itself goes back to 1 MSS.
7. **Plain answer**: So the answer is: CongWin starts at 1 MSS, rises exponentially until the threshold, then rises additively; at timeout, the threshold is set to half the old CongWin and CongWin resets to 1 MSS. Follow my arrow as the whole path.
   - board: `grow, then reset`
   - sketch: `flowchart LR ; A[Start 1 MSS] --> B[Slow Start] ; B --> C[Reach threshold] ; C --> D[Additive Increase] ; D --> E[Timeout] ; E --> F[Reset 1 MSS]`

Missing: doubling: MISSING; concrete_threshold: MISSING

## flowchart_invalid_twice, run 1

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 22.454 s, 5 steps, model gpt-5.5.

**Invalid Input Twice in a Validation Loop**: This flowchart keeps sending the user back to read input whenever the decision says “No.” If the input is invalid twice, the error path runs twice before the program can move on.

1. **Find the loop that answers it**: Your question lives in this validation loop. I’m circling the decision point, because every input must pass through this “Valid?” check before anything else can happen.
2. **First invalid input goes down**: Start by following one try: the program reads input, then asks “Valid?” If the answer is No, my red arrow drops to “Show error.”
   - board: `check it` · `invalid` · `1st error`
3. **The loop returns to try again**: After the error, the arrow loops back to “Read input.” That means the program does not end; it asks the user for another value.
   - board: `try again` · `ask again`
4. **Second invalid input repeats the same path**: If the second input is invalid too, it follows the same red No path again. So “Show error” happens a second time, then the loop sends us back again.
   - board: `2nd check` · `No again` · `2nd error`
5. **Only valid input exits the loop**: The answer is: invalid twice means two errors and two returns to input. Only when “Valid?” becomes Yes does the program process data and reach End.
   - board: `passes` · `finish`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`

## flowchart_invalid_twice, run 2

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 15.002 s, 5 steps, model gpt-5.5.

**Invalid Twice in an Input Loop**: The flowchart keeps sending invalid input to the error box, then back to reading input. If the input is invalid twice, the same error-and-retry path happens twice before the program can move on.

1. **Find the loop path**: Great question: if input is invalid twice, we follow the loop path twice. I’m circling the decision where the flowchart asks whether the input is valid.
2. **First invalid input**: On the first bad try, the answer at the diamond is No. Follow my arrow down to Show error: that means the program tells the user the input failed.
   - board: `bad try 1` · `warn user`
3. **Retry after the error**: After the error, the big return arrow sends us back to Read input. So the program does not end; it asks for another input.
   - board: `retry`
4. **Second invalid input**: If the second input is invalid too, the flow repeats exactly the same way. We go from Read input to Valid?, then No to Show error again.
   - board: `try 2` · `bad try 2` · `still fails`
5. **The plain answer**: So after two invalid inputs, Show error happens twice and the user is sent back to Read input twice. Only a Yes from Valid? lets the program process data and end.
   - board: `valid exits`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`

## flowchart_invalid_twice, run 3

Question: "What happens if the input is invalid twice?" (flowchart_loop.png)
Score 5/5 (path PASS, no_branch PASS, loop_back PASS, twice PASS, exit PASS). Lesson 12.764 s, 5 steps, model gpt-5.5.

**Invalid Input Twice in a Validation Loop**: This flowchart keeps returning to “Read input” whenever the decision “Valid?” is No. If the input is invalid twice, the error path happens twice, then the loop asks for input a third time.

1. **Find the loop that answers it**: Your question lives in this validation loop. I’ll circle the decision point, because every attempt depends on whether “Valid?” says Yes or No.
2. **First invalid input follows No**: On the first bad try, follow my red arrow from “Valid?” down the No path. The program shows the error instead of processing the data.
   - board: `No path` · `1st error`
3. **Then it loops back to ask again**: After the error, the flow does not end. It loops back to “Read input,” so the user gets another chance.
   - board: `try again`
4. **Second invalid input repeats the same path**: If the second input is invalid too, nothing new or special happens. The flow hits “Valid?” again, goes No again, and shows the second error.
   - board: `check again` · `No again` · `2nd error`
5. **Plain answer: invalid twice means two repeats**: So the answer is: invalid twice means two error messages and two trips back to input. Only when “Valid?” becomes Yes does the flow move on to process data and end.
   - board: `Yes exits`
   - sketch: `flowchart LR ; A[Read input] --> B[Valid?] ; B -->\|No\| C[Show error] ; C --> A ; B -->\|Yes\| D[Process data] ; D --> E[End]`

