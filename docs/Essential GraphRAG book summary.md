# Essential GraphRAG

## Section 3 - Advanced vector retrieval strategies

- Hybrid search highlighted as an imporant contributor to good RAG recall
    - A full text search index is needed on the text chunk
    - A vector index is needed in the vector embeddings
- Techniques like Parent Document Retrieval is also a good approach
    - it seems like, with neo4j, a full document (the whole pdf), andsplit it into smaller documents or Parent document, and then those are split further into childs, which are going to get embedded.
    
    This creates a graph structure that connects the childs with the whole document, there can be some smart ways to chunk this parent documents, depending on the token length is one of them.
    
    ![image.png](./img/image.png)
    
    section 3.2 - parent document retriever
    
    ![image.png](./img/image%201.png)
    

Figure 3.5 Graph visualization of part of the imported data in Neo4j Browser

## Section 4 - Generating Cypher queries from natural language
questions

The mistery of Text2Cypher queries follows this basic approach

- Retrieve the question from the user.
- Retrieve the schema of the knowledge graph.
- Define other useful information like terminology mappings, format instruc-
tions, and few-shot examples.
- Generate the prompt for the LLM.
- Pass the prompt to the LLM to generate the Cypher query.

![image.png](./img/image%202.png)

Figure 4.1 Workflow for generating Cypher queries from natural language questions

**Important!**

> 
> 
> 
> Text2cypher could also function as a “catchall” retriever for the types of questions
> where there’s no real good match for any of the other retrievers in the system.
> 

### Useful practices for query language generation

Few-shot examples are a great way to improve the performance of LLMs for text2-
cypher. 

The few-shot examples are specific to the knowledge graph being queried, so they
need to be created manually for each knowledge graph. This is very useful when you
recognize that the LLM misinterprets the schema or often makes the same type of
mistake (expects a property when it should be a traversal, etc.).

### Using database schema in the prompt to show the LLM the
structure of the knowledge graph

Letting the LLM know the schema of the graph knowledge base is crucial to generate correct cypher queries

To automatically infer the schema from Neo4j could be expensive, depending on the size of the data, so it’s common to sample the database and infer the schema from that. To infer the schema from Neo4j, we currently need to use procedures from the APOC library that’s free and available both within Neo4j’s SaaS offering Aura and in the other distributions of Neo4j. The following listing shows how you can infer the schema from a Neo4j database.

We then get the schema of the graph database and use it in the prompt to the LLM. we can store the schema in a structured way to generate a string that our LLM can understand, basically, showing the LLM how is the graph constructed

### Adding terminology mapping to semantically map the user
question to the schema

The LLM needs to know how to map the terminology used in the question to the ter-
minology used in the schema.

> 
> 
> 
> A well-designed graph schema uses nouns and verbs for
> 
> labels and relationship types and adjectives and nouns for properties.
> 

> 
> 
> 
> These mappings are knowledge graph specific and should be part of the
> prompt; they would be hard to reuse between different knowledge graphs.
> 

### Specialized text2cypher LLMs

Our open source training data at Hugging Face is available at: [huggingface.co/datasets/neo4j/text2cypher](https://huggingface.co/datasets/neo4j/text2cypher)

Neo4j also provides fine-tuned models based on open source LLMs (like Gemma2, Llama 3.1) at:
[huggingface.co/neo4j](https://huggingface.co/neo4j)

### Summary

- Query language generation fits in well with the RAG pipeline as a complement to other retrieval methods, especially when we want to aggregate data or get specific data from the graph.
- Useful practices for query language generation include using few-shot examples, schema, terminology mappings, and format instructions.
- We can implement a text2cypher retriever using a base model and structure the prompt to the LLM.
- We can use specialized (finetuned) LLMs for text2cypher and improve their performance.

## Section 5 - Agentic RAG

The starting interface to an agentic RAG system is usually a retriever router, whose job is to find the best-suited retriever (or retrievers) to perform the task at hand.

One common way to implement an agentic RAG system is to use an LLM’s ability to use tools (sometimes called function calling).

![image.png](./img/image%203.png)

A basic agentic system where the system only has to choose which retriever to use and decide whether the found context answers the question. I**n more advanced systems, the system might make up plans on what kind of tasks to perform to solve the task at hand.**

**Successful agentic RAG systems require a few foundational parts:**

- R**etriever router**—A function that takes in the user question(s) and returns the
best retriever(s) to use
- Retriever agents—The actual retrievers that can be used to retrieve the data
needed to answer the user question(s)
- Answer critic—A function that takes in the answers from the retrievers and
checks if the original question is answered correctly

### Retriever agents

A few generic retriever agents are relevant in most agentic RAG systems, like **vector similarity search** and **text2cypher**. The former is useful for **unstructured data** sources and the latter for s**tructured data** in a graph database, but in a real-world production system, it’s not trivial to make any of them perform at par with user expectations.

> 
> 
> 
> That’s why we need specialized retrievers that are very narrow but perform very well at what they’re meant for. These specialized retrievers can be built over time as we identify questions that the generic retrievers have problems generating queries to answer.
> 

### Retriever router

To pick the right retriever for the job, we have something called a retriever router. The retriever router is a function that takes in the user's question and returns the best retriever(s) to use. How the router makes this decision can vary, but usually, an LLM is used to make this decision.

### Answer critic

The answer critic is a function that takes in the answers from the retrievers and checks whether the original question is answered correctly. The answer critic is a blocking function that can stop the answer from being returned to the user if the answer is not correct or is incomplete.

### Why use Agentic RAG?

One area where agentic RAG is useful is when we have a variety of data sources and we want to use the best data source for the job. Another common usage is when the data source is very broad or complex and we need specialized retrievers to retrieve the data we need consistently.

This is where agentic RAG can be useful. A variety of retrievers are available, and we need to use the best retriever for the job and assess the answer before returning it to the user. In a production environment, this is very useful to keep the performance of the system high and the quality of the answers consistent.

### How to implement agentic RAG

An interesting approach is presented regarding tool calls, rather than the main agent calling a tool, it seems that an agent decomposes the user query, and then selects a list of tool calls that could answer the question this is then sent to a function that handles calling all the tools for the main agent, passing all the required arguments to make use of each tool.

The LLM can decide that it wants to make multiple function calls to respond to a single question.

> How is this different from toolcalling with AI-SDK or Mastra? is this approach better? how can AI-SDK or Mastra agents call multiple tools if needed?
> 

Another important point raised, is how multiple toolcalls, can be chained in a way that as the questions are being answered, the latter can be used to enhance the next queries

> 
> 
> 
> One extra benefit of sending the questions in sequence is that we can use the answers from the previous questions to rewrite the next question. This can be useful if the user asks a follow-up question that is dependent on the answer to the previous question. 
> 
> Consider the following example: “Who has won the most Oscars, and is that person alive?” A rewrite of this question could be “Who won the most Oscars?” and “Is that person alive?” where the second question is dependent on the answer to the first question.
> 
> So once we have the answer to the first question, we want to update the remaining
> questions with the new information. This can be done by calling a query updater with the original question and the answers from the retrievers. The query updater updates the existing questions with the new information.
> 

This seems to me like passing the history of the chat to the agent/tool, and rewriting the question based on past answers or the context of the conversation, but Im not a 100% sure about this

### Retriever router Instructions

The retriever router will select the best tools fot the job, and the arguments they need, here is the provided example

![image.png](./img/image%204.png)

Then this is the proposed  Agentic RAG Function, where the following is happening:

- The user query gets updated based on the current user query and the past answers
    - Seems like chat history, although they mentioned updating the query based on the last response
- The retriever router is called, it will then decide which tools and arguments to use, call them and return the answer
- The answer then gets appended to the chat history, with the common interface of
    
    ```python
    {"role":"assistant", 
    "content":f"For the question:'{updated_question}' 
    we have the answer: '{json.dumps(response)}'"
    }
    ```
    

![image.png](./img/image%205.png)

### Implementing the answer critic

LLMs are non-deterministic, so erros might and will occur, that is why the need for an answer critique step is essential

![image.png](./img/image%206.png)

> This is what was implemented for the AI-SDK version, this also implements structured outputs for the answer critique
> 

Some ideas for the Main agent system prompt are described in the text as:

![image.png](./img/image%207.png)

### Summary

- Agentic RAG is a system where a variety of retrieval agents are available to
retrieve the data needed to answer the user question.
- The main interface to an agentic RAG system is usually some kind of use case or
retriever router, whose job is to find the best-suited retriever (or retrievers) to
perform the task at hand.
- The foundational parts of an agentic RAG system are retriever agents, retriever
router, and answer critic.
- The main parts of an agentic RAG system can be implemented using an LLM
with tools/function-calling support.
- The retriever agents can be generic or specialized and should be added over
time as needed to improve the performance of the application.
- The answer critic is a function that takes in the answers from the retrievers and
checks if the original question is answered correctly.

## Section 6 - Constructing knowledge graphs with LLMs

### Extracting structured data from text

This is a common example of how regular vector search could end up pulling information from different unrelated documents, and assessing them as relevant, when in reality the user is asking for something specific related to one document. This completely undermines the relevance of the RAG pipeline

![image.png](./img/image%208.png)

### Structured outputs

Structured outputs are the basis of extracting information from unstructured documents

![image.png](./img/image%209.png)

> Since you’re a software engineer and not a legal expert, it’s important to consult someone with domain knowledge to determine which information is most important to extract. Additionally, speaking with end users about the specific questions they want answered can provide valuable insights.
> 

Combining structured output with a good system promp, guides the LLM into doing a better job

![image.png](./img/image%2010.png)

### Constructing the graph

First, you should design a suitable graph model that represents the relationships and entities in
your data. Graph modelling is beyond the scope of this book, but you can use LLMs to assist in defining the graph schema or look at other learning material, such as Neo4j Graph Academy.

![image.png](./img/image%2011.png)

Defining constraints and indexes is important to ensure the integrity of the graph, but it also enhances query performance. 

![image.png](./img/image%2012.png)

### Entity resolution

> 
> 
> 
> Entity resolution refers to the process of identifying and merging different representations of the same real-world entity within a dataset or knowledge graph.
> 

Techniques used in entity resolution include string matching, clustering algorithms, and even machine learning methods that use the context surrounding each entity to detect and resolve duplicates.

One of the most effective strategies is to develop **domain-specific ontologies** or rules that reflect your particular data context.

Additionally, using subject matter experts to define matching criteria and using iterative feedback loops—where potential matches are verified or corrected—can greatly improve accuracy. By combining **domain expertise** with **context-aware machine learning** or **clustering** techniques, you can develop a more robust and flexible approach to entity resolution. This will ensure that you capture the subtle details that matter most in your unique data environment.

Knowledge graphs, with the advent of LLMs, are being used to store both structured and unstructured text

![image.png](./img/image%2013.png)

### Summary

- Simply chunking documents for retrieval can result in inaccurate or mixed results, especially in domains like legal documents, where document boundaries matter.
- Retrieval tasks like filtering, sorting, and aggregating require structured data, as text embeddings alone are not suited for such operations.
- LLMs are effective at extracting structured data from unstructured text, converting it into usable formats like tables or key–value pairs.
- Structured output features in LLMs allow developers to define schemas, ensuring responses follow a specific format and reducing the need for postprocessing.
- Defining a clear data model with attributes such as contract type, parties, and dates is essential for guiding LLMs to extract relevant information accurately.
- Entity resolution in knowledge graphs is important for merging different representations of the same entity, improving data consistency and accuracy.
- Combining structured and unstructured data in knowledge graphs preserves the richness of the source material while enabling more precise querying.

## Section 7 - Microsoft’s GraphRAG implementation

What distinguishes MS GraphRAG is that, once the knowledge graph has been constructed, graph communities are detected, and domain-specific summaries are generated for groups of closely related entities. This layered approach transforms fragmented pieces of information from various text chunks into a cohesive and organized representation of information about specified entities, relationships, and communities.

One of the main points in the MSGraph approach is to extract entities and relationships from each chunk, then import all the discovered entities and relationships to a graph-database, building a structured graph representation of the text

This approach of using LLMs to generate entity descriptions and relations, ends up generating multiple descriptions for entities and relationships across entities, therefore, another step is required to reduce the amount of noise while still preserving important information

- Entity summarization
    - LLM is given all descriptions for a given entity, then it is tasked to generate a consolidated description, capturing all important aspects present in the given list of descriptions
- Relationshipt summarization
    - LLM is given all relationships between 2 entities, then it is tasked to generate a consolidated relationship, capturing all important aspects present in the given list of relationships

### Community detection and summarisation

A community is a group of entities that are more densely connected to each other than to the rest of the graph.

![image.png](./img/image%2014.png)

After this, the Louvain method is applied to identify groups of densely connected entities within the graph. Followed by a community summarisation process, which is executed for every detected community node by the Louvian method. The goal is to produce high-quality summaries that can be effectively used downstream for RAG. These community summaries consolidate key entities, relationships, and significant insights.

### Graph retrievers

- Local search
    - retrieves information from entities closely connected within a detected community
    - The local search method enhances LLM responses by combining structured knowledge graph data with unstructured text from source documents. This approach is particularly effective for entity-focused queries
    
    ![image.png](./img/image%2015.png)
    
    - A ranking of all the extracted information is necessary to keep it manageable
        - Text chunks are ranked by how frequently they are associated with relevant entities and limited to the top topChunks.
        - Community descriptions are ordered by rank and weight, selecting only the topCommunities.
        - Relationships are ranked by their importance and limited to topInsideRels.
        - Finally, entity summaries are retrieved without additional ranking constraints. This ensures only the most relevant information is included in the response.
- Global search
    - considers the entire graph structure to find the most relevant information.
    - Global search in GraphRAG uses community summaries as intermediate responses to efficiently answer queries that require aggregating information across the entire dataset.
    
    ![image.png](./img/image%2016.png)
    

### Summary

- MS GraphRAG uses a two-stage process where entities and relationships are first extracted and summarized from source documents, followed by community detection and summarization to create a cohesive knowledge representation.
- The extraction process uses LLMs to identify entities, classify them by predefined types (e.g., PERSON, GOD, LOCATION), and generate detailed descriptions of both entities and their relationships, including relationship strength scores.
- Entity and relationship descriptions from multiple text chunks are consolidated through LLM-based summarization to create unified, nonredundant representations that preserve key information.
- The system detects communities of densely connected entities using algorithms like the Louvain method and then generates community-level summaries to capture higher-level themes and relationships.
- Global search uses community summaries to answer broad, thematic queries through a map-reduce approach.
- Local search combines vector similarity search with graph traversal to answer entity-focused queries.
- The effectiveness of retrieval depends on factors like chunk size, entity type selection, and community detection parameters, with smaller chunks generally leading to more comprehensive entity extraction.
- The system handles potential scaling challenges through ranking mechanisms for managing large numbers of entities, relationships, and communities while maintaining context relevance.

## Section 7- RAG appliacation evaluation

![image.png](./img/image%2017.png)

To evaluate the system comprehensively, you need well-defined end-to-end test examples. Each example consists of a question and its corresponding ground truth response.

> Having dynamic test cases or ground truths, is essential for having a benchmark that remains valid even if the underlying data of the knowledgebase changes
> 

### RAGAS

A framework designed for evaluating RAG systems based on three key metrics

- Context recall
    - Context recall measures how many relevant pieces of information were successfully retrieved using the prompt in “Context recall evaluation.”
    - The prompt in “Context recall evaluation” ensures that every sentence in the generated answer is explicitly supported by the retrieved context.
- Faithfulness
    - Evaluates whether the generated response remains factually consistent with
    the retrieved context. A response is considered faithful if all its claims can be directly supported by the provided documents, minimising the risk of hallucination.
- Correctness
    - Answer correctness assesses how accurately and completely the response addresses the
    user’s query. It considers both factual accuracy and relevance to ensure the response aligns with the intent of the question.

### Summary

- Evaluating a RAG pipeline is crucial for ensuring accurate and coherent answers. A benchmark evaluation helps measure performance and define the agent’s capabilities.
- The evaluation process involves assessing various stages: retrieval tool selection, context retrieval relevance, answer generation quality, and overall system effectiveness.
- A well-structured benchmark dataset should include diverse queries that test retrieval accuracy, entity mapping, the handling of greetings, irrelevant queries, and various Cypher-based database lookups.
- Instead of static expected answers, using Cypher queries as ground truth ensures the benchmark remains valid even if the underlying data changes
- Instead of static expected answers, using Cypher queries as ground truth ensures the benchmark remains valid even if the underlying data changes.
- Context recall measures how well the system retrieves relevant information.
- Faithfulness evaluates if the generated answer is factually consistent with the
retrieved content.
- Answer correctness assesses whether the response fully and accurately addresses
the query.