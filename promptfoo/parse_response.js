// Reads the chatbot's /api/chat reply. The answer is what gets tested; the
// company documents travel along as metadata so the grader can see them.
module.exports = (json) => {
  if (json.source !== 'live') {
    // A saved backup answer is not a fresh test result.
    return { error: `Not a live answer (${json.source_label || json.source}). Check the app and API key.` };
  }
  return {
    output: json.response,
    metadata: {
      companyDocuments: json.retrieved_context,
      sources: (json.sources || []).map((doc) => doc.filename),
    },
  };
};
