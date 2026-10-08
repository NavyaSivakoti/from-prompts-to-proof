// Builds what the grader reads: the question, any earlier messages, the exact
// company documents the chatbot was given, and the chatbot's answer.
module.exports = (output, context) => {
  const vars = (context && context.vars) || {};
  const documents = context && context.metadata && context.metadata.companyDocuments;
  const history = JSON.parse(vars.history || '[]');
  const earlier = history.length
    ? history.map((message) => `${message.role}: ${message.content}`).join('\n')
    : '(none)';
  return [
    `Customer question:\n${vars.question}`,
    `Earlier conversation:\n${earlier}`,
    `Company documents given to the chatbot:\n${documents || '(none: no company document matched this question)'}`,
    `Chatbot answer:\n${output}`,
  ].join('\n\n');
};
