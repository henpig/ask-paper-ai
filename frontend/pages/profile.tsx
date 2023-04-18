import { useContext, useEffect, useState } from "react"
import { GuestUserContext, useGuestSession } from "../hooks/session"
import { useSession } from "next-auth/react"
import { Flex } from "../components/styles/flex"
import { Avatar, Spacer, Text, styled } from "@nextui-org/react"
import Info from "../components/info"
import MarkdownView from "react-showdown"
import { loadDatasetsForUser } from "../service/service"
import { makeLinksClickable } from "."
import Link from "next/link"


const Div = styled('div', {
    width: '100vw',
    height: '100vh',
    overflow: 'scroll',
})

const Profile = () => {
    const { isUserLoggedInAsGuest } = useContext(GuestUserContext)
    const { data: session } = isUserLoggedInAsGuest ? useGuestSession() : useSession()
    const [userDatasets, setUserDatasets] = useState<string | undefined>(undefined)

    useEffect(() => {
        // @ts-ignore 
        if (!session!.accessToken || !session!.user!.email) return
        // @ts-ignore 
        loadDatasetsForUser(session!.user!.email, session!.accessToken)
            .then(res => {
                console.log(res)
                console.log(res.data)
                setUserDatasets(res.data.datasets)
            })
    }, [session])

    return (<>
        <Div as="main" css={{padding: "$5"}}>
            <Flex direction='column' css={{ overflow: 'scroll', alignItems: 'flex-start' }}>
                <Flex css={{ gap: "$4" }}>
                    <Avatar
                        size="lg"
                        src={session!.user!.image!}
                        color="warning"
                        bordered
                    />
                    <Text>{session!.user!.email}</Text>
                </Flex>
                <Spacer y={2} />
                <Flex direction='column' css={{ margin: "$3", alignItems: 'flex-start'}} data-testid="profile-dataset-area">
                    <Text h4>📊 My Extracted Datasets</Text>
                    {isUserLoggedInAsGuest
                        ? <Info>This feature is only available to Community Members</Info>
                        : <MarkdownView
                            markdown={makeLinksClickable(userDatasets ?? 'No datasets found.')}
                            options={{ tables: true, emoji: true }}
                        />
                    }
                </Flex>

                <Spacer y={2} />
                <Link href="/">← Go back to app</Link>
            </Flex>
        </Div>
    </>)
}
export default Profile