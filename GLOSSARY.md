# RAG Course Project

Course project that answers questions over documents and data using AWS Bedrock models. The notebooks are the reference; the Python project is their runnable port.

## Language

**Source**:
A body of knowledge a question is asked against: a set of web pages, a PDF, or a SQL database.
_Avoid_: Dataset, corpus, input

**Pipeline**:
The full path from a question over one Source to an answer. There are three: web, PDF and SQL.
_Avoid_: Chain, flow, notebook (a notebook is only the course form of a Pipeline)

**Core**:
The shared model, embedding and prompt setup that every Pipeline uses.
_Avoid_: Common, utils, shared

**Offline test**:
A test that runs with no AWS access, with Bedrock calls replaced by fakes.
_Avoid_: Unit test (too broad), mock test

**Live test**:
A test that calls real Bedrock models. Run by hand only.
_Avoid_: Integration test, e2e
