import {Button, CSS, Input, Modal, Radio, Text, Textarea} from '@nextui-org/react';
import {Flex} from "./styles/flex";
import React, {useState} from "react";
import axios from "axios";
import {Paper} from "../pages";
import useCustomSession from "../hooks/session";


interface FeedbackProps {
  paper: Paper,
  answer: string,
  question: string,
  userEmail: string
  css?: CSS,
}

const Feedback = ({css, userEmail, paper, answer, question}: FeedbackProps) => {
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [visible, setVisible] = useState(false);
  const [accuracy, setAccuracy] = useState<boolean | undefined>(undefined);
  const [sentiment, setSentiment] = useState<string | undefined>(undefined);
  const [message, setMessage] = useState<string | undefined>(undefined);
  const {data: session} = useCustomSession()

  function storeFeedback(email: string, sentiment: string, message: string, paper: Paper, question: string, answer: string) {
    return axios.post(`${process.env.NEXT_PUBLIC_BACKEND_APIURL}/store-feedback`, {
      "table_name": "HippoPrototypeFeedback",
      "data": {
        email,
        sentiment,
        message,
        paper_id: paper.id,
        question,
        answer,
      }
    }, {
      headers: {
        'Content-Type': 'application/json',
        // @ts-ignore
        'Authorization': `Bearer ${session!.accessToken}`,
      },
    })
  }


  if (success) {
    return (<Text>Thank you {session?.user?.name ?? ''}! 🙏</Text>)
  }
  return (
    <>
      <Text h5>Can you help us improve? 🚀</Text>
      <Flex css={{gap: "$7"}}>

        <Button ghost auto color="success" size="lg" iconRight="👍"
                css={{color: 'green', '&:hover': {color: 'white'}}}
                onPress={() => {
                  setVisible(true)
                  setAccuracy(true)
                }}
        >
          Answer was accurate
        </Button>
        <Button ghost auto size="lg" iconRight="👎"
                onPress={() => {
                  setVisible(true)
                  setAccuracy(false)
                }}
        >
          Answer was inaccurate
        </Button>
      </Flex>
      <Modal
        closeButton
        aria-labelledby="feedback-modal"
        open={visible}
        onClose={() => setVisible(false)}
        width={'fit-content'}
      >
        <Modal.Header>
          <Text css={{textDecoration: 'underline'}} id="feedback-modal" span size={20}>
            Hippo's <Text b>Feedback form </Text>
          </Text>
        </Modal.Header>
        <Modal.Body>
          <Flex direction="column" css={{gap: "$10"}}>
            <Flex css={{gap: "$4"}}>
              <label htmlFor='email'>Submitting as</label>
              <Input
                readOnly
                id="email"
                name="email"
                initialValue={userEmail}
                width={"300px"}
              />
            </Flex>
            <label htmlFor='sentiment'>How do you feel about the tool?</label>
            <Radio.Group
              value={sentiment}

              onChange={setSentiment}
              isRequired
              name="sentiment"
              id="sentiment"
            >
              <Radio value="Very bad">😡️</Radio>
              <Radio value="Good">😕</Radio>
              <Radio value="Bad">🙂</Radio>
              <Radio value="Very good">😍</Radio>
            </Radio.Group>
            <Flex direction="column" css={{width: "100%", gap: "$4"}}>

              <label htmlFor='message'>Extra comments:</label>
              <Textarea
                bordered
                name='message'
                data-testid='message'
                id='message'
                minRows={2}
                maxRows={20}
                onChange={e => setMessage(e.target.value)}
                placeholder='Please provide extra comments! This could be anything from a bug report to a feature request.'
                // @ts-ignore
                css={{width: "400px"}}
              />
            </Flex>
            {error && <Text color="error">{error}</Text>}
            <Modal.Footer>
              <Button auto flat color="error" onPress={() => setVisible(false)}>
                Close
              </Button>
              <Button onClick={() => {
                if (userEmail && sentiment) {
                  storeFeedback(userEmail, sentiment, message ?? 'No message provided', paper, question, answer)
                    .then(() => setSuccess(true))
                    .catch(e => {
                      console.error(e)
                      setError("Something went wrong :(")
                    })
                } else {
                  setError("Please check one of the options.")
                }
              }}>Submit 🚀</Button>
            </Modal.Footer>
          </Flex>
        </Modal.Body>
      </Modal>
    </>
  )
};

export default Feedback;