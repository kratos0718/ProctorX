# seed_subjects.py
# Run this ONCE to add DSA, DBMS, Java, DAA questions
# Usage: py -3.11 seed_subjects.py

import sys
sys.path.insert(0, '.')
from app import app, db
from models import Question

questions = [
  # ── DSA ──────────────────────────────────────────────────────
  ("Data Structures & Algorithms","What is the time complexity of binary search?","O(n)","O(log n)","O(n log n)","O(1)","B"),
  ("Data Structures & Algorithms","Which data structure uses LIFO order?","Queue","Stack","Array","Linked List","B"),
  ("Data Structures & Algorithms","What is the worst-case time complexity of QuickSort?","O(n log n)","O(n)","O(n²)","O(log n)","C"),
  ("Data Structures & Algorithms","A binary tree with n nodes has at most how many levels?","log n","n","n/2","2n","A"),
  ("Data Structures & Algorithms","Which traversal visits root node first?","Inorder","Postorder","Preorder","Level order","C"),
  ("Data Structures & Algorithms","What is the space complexity of merge sort?","O(1)","O(log n)","O(n)","O(n²)","C"),
  ("Data Structures & Algorithms","In a min-heap, the root always contains the?","Maximum element","Minimum element","Middle element","Random element","B"),
  ("Data Structures & Algorithms","Which graph algorithm finds the shortest path?","DFS","Prim's","Dijkstra's","Kruskal's","C"),
  ("Data Structures & Algorithms","What is the time complexity of inserting into a hash table (average)?","O(n)","O(log n)","O(1)","O(n log n)","C"),
  ("Data Structures & Algorithms","Which sorting algorithm is stable by default?","Quick Sort","Heap Sort","Selection Sort","Merge Sort","D"),

  # ── DBMS ─────────────────────────────────────────────────────
  ("Database Management Systems","What does ACID stand for in database transactions?","Atomicity Consistency Isolation Durability","Atomic Consistent Integrated Distributed","Availability Consistency Integrity Durability","Atomicity Concurrency Isolation Distribution","A"),
  ("Database Management Systems","Which normal form removes partial dependencies?","1NF","2NF","3NF","BCNF","B"),
  ("Database Management Systems","What SQL command is used to retrieve data?","INSERT","UPDATE","SELECT","DELETE","C"),
  ("Database Management Systems","A primary key can contain?","Duplicate values","NULL values","Both duplicates and NULLs","Neither duplicates nor NULLs","D"),
  ("Database Management Systems","Which join returns all records from both tables?","INNER JOIN","LEFT JOIN","RIGHT JOIN","FULL OUTER JOIN","D"),
  ("Database Management Systems","What is a foreign key?","A key that uniquely identifies a record","A key referencing another table's primary key","A composite key","An alternate key","B"),
  ("Database Management Systems","Which isolation level prevents dirty reads?","READ UNCOMMITTED","READ COMMITTED","REPEATABLE READ","SERIALIZABLE","B"),
  ("Database Management Systems","What does DDL stand for?","Data Definition Language","Data Deletion Language","Data Distribution Language","Data Driven Logic","A"),
  ("Database Management Systems","Which command permanently saves a transaction?","ROLLBACK","SAVEPOINT","COMMIT","BEGIN","C"),
  ("Database Management Systems","What is denormalization?","Adding more normal forms","Intentionally introducing redundancy for performance","Removing all redundancy","Splitting tables","B"),

  # ── OS ─────────────────────────────────────────────────────
  ("Operating Systems","What is a process in OS terminology?","A program in execution","A system utility","A file stored on disk","A memory block","A"),
  ("Operating Systems","Which scheduling algorithm minimizes average waiting time?","FCFS","Round Robin","SJF (Shortest Job First)","Priority","C"),
  ("Operating Systems","What causes thrashing?","Too many interrupts","Excessive page faults","Disk failure","CPU overheating","B"),
  ("Operating Systems","What does a semaphore primarily solve?","Deadlock","Starvation","Mutual Exclusion","Thrashing","C"),
  ("Operating Systems","Which deadlock condition implies non-preemption?","Hold and wait","Circular wait","No preemption","Mutual exclusion","C"),
  ("Operating Systems","What is an orphan process?","A process with no PID","A process whose parent has terminated","A background daemon","A shell script","B"),
  ("Operating Systems","What is the purpose of demand paging?","Load pages only when needed","Load all pages at startup","Send pages to cache","Page replacement policy","A"),
  ("Operating Systems","What translates logical addresses to physical addresses?","CPU","MMU (Memory Management Unit)","ALU","Operating System Kernel","B"),
  ("Operating Systems","Which of these is not an OS?","Windows","Linux","macOS","Apache","D"),
  ("Operating Systems","What is context switching?","Saving the state of one process and loading another","Switching users","Changing CPU modes","Rebooting the OS","A"),

  # ── Computer Networks ──────────────────────────────────────
  ("Computer Networks","Which layer of the OSI model handles routing?","Transport","Data Link","Network","Physical","C"),
  ("Computer Networks","What is the port number for HTTP?","443","21","80","25","C"),
  ("Computer Networks","Which protocol provides reliable, connection-oriented data delivery?","UDP","ICMP","IP","TCP","D"),
  ("Computer Networks","What does DNS do?","Encrypts data","Translates domain names to IP addresses","Routes packets","Assigns IP addresses dynamically","B"),
  ("Computer Networks","Which device operates at the Data Link layer?","Router","Hub","Switch","Repeater","C"),
  ("Computer Networks","What is the length of an IPv4 address?","16 bits","32 bits","64 bits","128 bits","B"),
  ("Computer Networks","Which of these is a private IP address?","8.8.8.8","192.168.1.10","17.5.7.8","200.100.50.25","B"),
  ("Computer Networks","What protocol is used to ping a device?","TCP","UDP","IGMP","ICMP","D"),
  ("Computer Networks","Which algorithm avoids network congestion?","Dijkstra","AIMD (Additive Increase Multiplicative Decrease)","AES","RSA","B"),
  ("Computer Networks","What does MAC stand for?","Media Access Control","Multiple Access Carrier","Machine Address Code","Memory Access Controller","A"),

  # ── Machine Learning ───────────────────────────────────────
  ("Machine Learning","Which algorithm is used for Classification?","Linear Regression","K-Means","Logistic Regression","PCA","C"),
  ("Machine Learning","What is overfitting?","Model performs poorly on both training and test data","Model performs well on training but poor on test data","Model performs excellent on test data","Model generalizes perfectly","B"),
  ("Machine Learning","Which of the following is Unsupervised Learning?","Decision Trees","Clustering","Neural Networks","SVM","B"),
  ("Machine Learning","What does an SVM try to maximize?","Accuracy","Margin between classes","Entropy","Information Gain","B"),
  ("Machine Learning","What happens in the Gradient Descent algorithm?","Minimizes the loss function","Maximizes the loss function","Reduces learning rate","Normalizes data","A"),
  ("Machine Learning","Which metric is best for imbalanced datasets?","Accuracy","F1 Score","MSE","Sum of Squared Errors","B"),
  ("Machine Learning","What does K refer to in KNN?","Kernel Trick","Number of features","Number of nearest neighbors","Number of iterations","C"),
  ("Machine Learning","Random Forest is an example of what technique?","Bagging","Boosting","Clustering","Dimensionality Reduction","A"),
  ("Machine Learning","In Naive Bayes, what does the 'naive' assumption mean?","Features are dependent","Features are independent","Features are linear","Data is normally distributed","B"),
  ("Machine Learning","What does the learning rate control?","Size of the dataset","Number of epochs","Step size finding the minimum","Depth of tree","C"),

  # ── Artificial Intelligence ────────────────────────────────
  ("Artificial Intelligence","Who is considered the father of AI?","Alan Turing","John McCarthy","Geoffrey Hinton","Yann LeCun","B"),
  ("Artificial Intelligence","Which search algorithm guarantees the shortest path in an unweighted graph?","DFS","BFS","A*","Hill Climbing","B"),
  ("Artificial Intelligence","What is the Turing Test designed to test?","Machine's ability to exhibit intelligent behavior equivalent to a human","Machine's speed","Machine's memory","Machine's learning curve","A"),
  ("Artificial Intelligence","Which algorithm uses a heuristic?","BFS","A* Search","DFS","Uniform Cost Search","B"),
  ("Artificial Intelligence","In Minimax, what does the 'Max' node do?","Minimizes opponent's score","Maximizes its own score","Evaluates random moves","Ends the game","B"),
  ("Artificial Intelligence","What is Alpha-Beta pruning?","A tree planting algorithm","Optimization technique for Minimax","A neural network layer","An clustering technique","B"),
  ("Artificial Intelligence","What does NLP stand for?","Natural Learning Process","Neural Language Processing","Natural Language Processing","New Learning Paradigm","C"),
  ("Artificial Intelligence","Expert systems rely heavily on?","Randomness","Knowledge Bases","Neural Networks","Genetic Algorithms","B"),
  ("Artificial Intelligence","Which logic uses variables, quantifiers, and predicates?","Propositional Logic","Fuzzy Logic","First Order Logic","Boolean Logic","C"),
  ("Artificial Intelligence","What is a perceptron?","A complex AI model","The simplest building block of a neural network","A search algorithm","A robotic sensor","B"),

  # ── Compiler Design ────────────────────────────────────────
  ("Compiler Design","Which phase of the compiler generates tokens?","Syntax Analysis","Semantic Analysis","Lexical Analysis","Code Generation","C"),
  ("Compiler Design","What does a parser do?","Generates machine code","Checks grammar and creates an AST","Removes comments","Optimizes code","B"),
  ("Compiler Design","Which grammar can Left Recursion cause problems for?","Top-Down Parsers","Bottom-Up Parsers","LR Parsers","LALR Parsers","A"),
  ("Compiler Design","What data structure does the Lexical Analyzer use to track identifiers?","Stack","Queue","Symbol Table","Hash Map","C"),
  ("Compiler Design","Which tool generates a Lexical Analyzer?","YACC","Bison","Lex/Flex","GCC","C"),
  ("Compiler Design","Semantic analysis primarily checks for?","Syntax errors","Missing semicolons","Type mismatches","Unreachable code","C"),
  ("Compiler Design","What is three-address code?","Machine code execution","Intermediate code representation","A memory addressing mode","Bytecode","B"),
  ("Compiler Design","Peephole optimization is applied to?","Source code","Target machine code","AST","Symbol Table","B"),
  ("Compiler Design","What is a typical optimization technique?","Dead code elimination","Adding variables","Increasing loops","Recursive descent","A"),
  ("Compiler Design","Which phase comes directly before Code Generation?","Lexical Analysis","Optimization","Semantic Analysis","Linker","B"),

  # ── Software Engineering ───────────────────────────────────
  ("Software Engineering","Which SDLC model is sequential and non-iterative?","Agile","Spiral","Waterfall","Scrum","C"),
  ("Software Engineering","What does Agile emphasize?","Heavy documentation","Rigid planning","Adaptability and working software","Cost overruns","C"),
  ("Software Engineering","What is a Unit Test?","Testing the whole system","Testing individual components or functions","Testing user interfaces","Beta testing","B"),
  ("Software Engineering","Which design pattern restricts class instantiation to one object?","Factory","Observer","Singleton","Adapter","C"),
  ("Software Engineering","What does UML stand for?","Unified Markup Language","Unified Modeling Language","Universal Modeling Logic","User Metric Layout","B"),
  ("Software Engineering","What is coupling?","Degree of interdependence between modules","Internal strength of a module","Version control merging","Database connecting","A"),
  ("Software Engineering","Is high cohesion good or bad?","Bad","Good","Irrelevant","Only in Agile","B"),
  ("Software Engineering","Which phase consumes the most time in maintaining software?","Development","Design","Testing","Maintenance","D"),
  ("Software Engineering","What is the Observer pattern?","Publish-subscribe relationship","Creating families of objects","Wrapping an interface","State machine management","A"),
  ("Software Engineering","What is Refactoring?","Rewriting software from scratch","Modifying structure without changing behavior","Testing code deeply","Porting to a new language","B"),

  # ── Distributed Systems ────────────────────────────────────
  ("Distributed Systems","What is the CAP theorem?","Consistency, Availability, Partition Tolerance","Concurrency, Availability, Performance","Compute, Access, Process","Cache, Append, Pull","A"),
  ("Distributed Systems","Which consensus algorithm is used by Raft?","Leader election","Proof of work","Practical Byzantine Fault Tolerance","Gossip protocol","A"),
  ("Distributed Systems","What is a vector clock?","A physical clock","A logical clock for ordering events","A network latency monitor","A CPU timer","B"),
  ("Distributed Systems","RPC stands for?","Remote Process Control","Remote Procedure Call","Random Process Count","Regional Protocol Configuration","B"),
  ("Distributed Systems","What is consistent hashing used for?","Cryptographic signing","Load balancing partitioned data smoothly","Minimizing database queries","Securing HTTP","B"),
  ("Distributed Systems","Which system exhibits Byzantine failures?","Systems that crash cleanly","Systems that show arbitrary or malicious failure","Systems with network partitions","Systems that are highly available","B"),
  ("Distributed Systems","What does MapReduce do?","Renders graphics","Process and generates large datasets","Caches web pages","Logs errors","B"),
  ("Distributed Systems","What is a network partition?","Splitting a database table","A communication break between nodes","A subnet mask","Firewall rule","B"),
  ("Distributed Systems","In a master-slave architecture, what does the master do?","Only stores backups","Dictates tasks and handles writes","Only handles reads","Routes external traffic","B"),
  ("Distributed Systems","What does replication achieve?","Code optimization","Minimizing storage","Fault tolerance and high availability","Encrypting data","C"),

  # ── Computer Architecture ──────────────────────────────────
  ("Computer Architecture","Which component acts as the brain of the CPU?","ALU","Control Unit","Registers","Main Memory","B"),
  ("Computer Architecture","What is pipelining?","Passing instructions through wires","Overlapping execution of multiple instructions","Water cooling the CPU","Linking multiple cores","B"),
  ("Computer Architecture","What is the fastest memory type?","L1 Cache","L3 Cache","Registers","RAM","C"),
  ("Computer Architecture","What describes Von Neumann architecture?","Shared memory for data and code","Separate memories for data and code","Parallel processing","GPU architecture","A"),
  ("Computer Architecture","What does RISC stand for?","Reduced Instruction Set Computer","Reliable Integration System Core","Random Instruction Sequence Compiler","Rate Interrupt System Clock","A"),
  ("Computer Architecture","What happens during a Cache Miss?","Data is fetched from slower memory","CPU crashes","Instruction is skipped","Registers flush","A"),
  ("Computer Architecture","Which mapping technique is used in caches?","Direct Mapping","Linear Mapping","Circular Mapping","Pointer Mapping","A"),
  ("Computer Architecture","What does the Program Counter (PC) hold?","Current instruction","Next instruction's address","Result of ALU","Interrupt flags","B"),
  ("Computer Architecture","What is Little Endian?","Smallest CPU","Least significant byte stored at lowest address","Most significant byte stored at lowest address","A networking protocol","B"),
  ("Computer Architecture","What defines Moore's Law?","Transistor count doubles roughly every two years","CPU speed doubles every year","Memory size doubles every 18 months","Power consumption halves every year","A")
]
with app.app_context():
  added = 0
  for q in questions:
    exam, qtext, a, b, c, d, ans = q
    exists = Question.query.filter_by(exam_name=exam, question_text=qtext).first()
    if not exists:
      db.session.add(Question(
        exam_name=exam, question_text=qtext,
        option_a=a, option_b=b, option_c=c, option_d=d,
        correct_answer=ans
      ))
      added += 1
  db.session.commit()
  print(f"[SUCCESS] Added {added} questions across 10 CS subjects!")
  total = Question.query.count()
  print(f"[INFO] Total questions in database: {total}")
