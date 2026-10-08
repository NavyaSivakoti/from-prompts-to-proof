// Builds what the grader reads: the question, the exact company documents the
// chatbot was given, and the chatbot's answer.
module.exports = (output, context) => {
  const vars = (context && context.vars) || {};
  const documents = context && context.metadata && context.metadata.companyDocuments;
  return [
    `Customer question:\n${vars.question}`,
    `Company documents given to the chatbot:\n${documents || '(none: no company document matched this question)'}`,
    `Chatbot answer:\n${output}`,
  ].join('\n\n');
};
